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
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

    command = event.get("command", "")
    args: list[str] = event.get("args", [])

    if not command:
        return {"statusCode": 400, "body": "Missing 'command' field"}

    if command == "import_sql":
        return _import_sql(event)

    full_command = [sys.executable, "manage.py", command, *args]
    logger.info("Executing: %s", " ".join(full_command))

    result = subprocess.run(
        full_command,
        capture_output=True,
        text=True,
        timeout=870,
    )

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
