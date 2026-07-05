# =============================================================================
# SSM Parameter Store — 管理者ロール専用シークレット
# =============================================================================
#
# 運営者（管理者ロール）専用の OpenAI API キーを SecureString で保管する。
# 一般ユーザーには使用させない（全員 BYOK 必須）。
#
# 設計書: docs/design/multi-client-ai-chat.md §5.5
#
# 値の運用ポリシー:
#   - 初回 Apply 時はダミー値（"PLACEHOLDER_SET_VIA_AWS_CONSOLE"）でリソースを作成
#   - 実キーは AWS Console / CLI から手動で上書き（terraform.tfvars に書かない = state にも残らない）
#   - lifecycle.ignore_changes = [value] で以降の差分検出を無視
# -----------------------------------------------------------------------------

resource "aws_ssm_parameter" "openai_admin_api_key" {
  name        = "/${var.project_name}/production/openai/admin-api-key"
  description = "Admin-only OpenAI API key (NOT for general users). Set the real value via AWS Console after first apply."
  type        = "SecureString"
  value       = "PLACEHOLDER_SET_VIA_AWS_CONSOLE"
  tier        = "Standard"

  tags = {
    Name    = "${var.project_name}-openai-admin-api-key"
    Purpose = "admin-only"
  }

  lifecycle {
    # 実キーは AWS Console から設定するため、value 差分を無視
    ignore_changes = [value]
  }
}
