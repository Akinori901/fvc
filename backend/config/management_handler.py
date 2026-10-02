"""Lambda handler for running Django management commands.

Usage:
    aws lambda invoke --function-name fvc-worker \
        --payload '{"command": "migrate"}' \
        --cli-binary-format raw-in-base64-out \
        response.json

    aws lambda invoke --function-name fvc-worker \
        --payload '{"command": "sync_prices", "args": ["--market", "JP"]}' \
        --cli-binary-format raw-in-base64-out \
        response.json

    aws lambda invoke --function-name fvc-worker \
        --payload '{"command": "import_sql", "s3_bucket": "fvc-bucket", "s3_key": "dbdump/fvc-data.sql.gz"}' \
        --cli-binary-format raw-in-base64-out \
        response.json
"""

from __future__ import annotations

import gzip
import logging
import os
import subprocess
import sys
from typing import Any

logger = logging.getLogger(__name__)

# 定期実行コマンドの既定タイムアウト（秒）。
# 実測の最長は sync_prices(JP) の約 110 秒。銘柄数に比例して伸びるため、
# 打ち切りでスナップショットが静かに欠けないよう倍以上の余裕を取る。
DEFAULT_COMMAND_TIMEOUT = 300

# 既定値では足りないコマンドの個別指定（秒）。Lambda 側の timeout は 900 秒なので、
# 後片付けの余地を残して 870 秒を上限とする。
# sync_news / sync_dividends は全銘柄を逐次処理するため現在 DISABLED だが、
# 手動実行や再開時に既定値で切られないようここで延ばしておく。
COMMAND_TIMEOUTS = {
    "sync_news": 870,
    "sync_dividends": 870,
    "migrate": 870,
    "loaddata": 870,
}


def _configure_logging() -> None:
    """ハンドラ自身のログを CloudWatch に出す。

    settings の LOGGING は django.setup() を通る manage.py 子プロセスにしか
    効かず、このハンドラは Django 設定を読まない経路で動く。Lambda ランタイムが
    先に root logger へハンドラを付けているため force=True で貼り直す。
    これがないと打ち切りや失敗が CloudWatch に何も残らない。
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
        force=True,
    )


def _import_sql(event: dict[str, Any]) -> dict[str, Any]:
    """Download a .sql.gz from S3 and execute against the Django DB (streaming)."""
    import boto3
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    django.setup()

    from django.db import connection

    bucket = event["s3_bucket"]
    key = event["s3_key"]
    local_path = f"/tmp/{os.path.basename(key)}"

    # Download from S3
    s3 = boto3.client("s3")
    s3.download_file(bucket, key, local_path)

    # Stream line by line to avoid loading entire file into memory
    cursor = connection.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
    executed = 0
    errors = []
    buf = []

    with gzip.open(local_path, "rt", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("--") or stripped.startswith("/*"):
                continue
            buf.append(line)
            if stripped.endswith(";"):
                statement = "".join(buf).strip().rstrip(";")
                buf.clear()
                if not statement:
                    continue
                try:
                    cursor.execute(statement)
                    executed += 1
                except Exception as e:
                    errors.append(f"stmt#{executed}: {str(e)[:200]}")
                    if len(errors) >= 20:
                        break

    cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
    os.remove(local_path)

    return {
        "statusCode": 0 if not errors else 1,
        "executed": executed,
        "errors": errors[:20],
    }


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Invoke a Django management command from Lambda event payload."""
    _configure_logging()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

    command = event.get("command", "")
    args: list[str] = event.get("args", [])

    if not command:
        return {"statusCode": 400, "body": "Missing 'command' field"}

    if command == "import_sql":
        return _import_sql(event)

    full_command = [sys.executable, "manage.py", command, *args]
    logger.info("Executing: %s", " ".join(full_command))

    # Lambda の 900 秒上限まで粘らせない。全銘柄を逐次処理していた頃は上限に
    # 張り付いて GB 秒を浪費していたため、正常時の実測（最長 110 秒）に対して
    # 余裕を持たせた値で頭打ちにし、異常時は早く落とす。
    # 上限に近い時間を要する重いコマンドは COMMAND_TIMEOUTS で個別に延ばす。
    timeout = COMMAND_TIMEOUTS.get(command, DEFAULT_COMMAND_TIMEOUT)

    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        # 打ち切りを Lambda の未処理例外にせず、原因の分かる結果として返す。
        stdout = e.stdout or ""
        stderr = e.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        logger.error("Command '%s' timed out after %ds. stderr: %s", command, timeout, stderr[-2000:])
        return {
            "statusCode": 1,
            "stdout": stdout[-4000:],
            "stderr": stderr[-4000:],
            "returncode": None,
            "timedOut": True,
            "timeout": timeout,
        }

    if result.returncode == 0:
        logger.info("Command '%s' succeeded. stdout: %s", command, result.stdout[-1000:])
    else:
        logger.error("Command '%s' failed (rc=%d). stderr: %s", command, result.returncode, result.stderr[-2000:])

    return {
        "statusCode": 0 if result.returncode == 0 else 1,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
        "returncode": result.returncode,
    }
