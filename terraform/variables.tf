variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "fvc"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "fair_value_calculator"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "fvc_admin"
  sensitive   = true
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

variable "django_secret_key" {
  description = "Django SECRET_KEY"
  type        = string
  sensitive   = true
}

variable "s3_bucket_name" {
  description = "S3 bucket name for frontend"
  type        = string
  default     = "fvc-bucket"
}

variable "basic_auth_user" {
  description = "Basic auth username for CloudFront"
  type        = string
  sensitive   = true
}

variable "basic_auth_pass" {
  description = "Basic auth password for CloudFront"
  type        = string
  sensitive   = true
}

# -----------------------------------------------------------------------------
# Cognito - Google Identity Provider
# -----------------------------------------------------------------------------
# 事前に Google Cloud Console で OAuth 2.0 Client ID を作成して取得する。
# 詳細: docs/design/cognito-oauth-migration.md §5.3
# -----------------------------------------------------------------------------

variable "google_oauth_client_id" {
  description = "Google OAuth Client ID (for Cognito federated identity)"
  type        = string
  sensitive   = true
}

variable "google_oauth_client_secret" {
  description = "Google OAuth Client Secret (for Cognito federated identity)"
  type        = string
  sensitive   = true
}

# Cognito 招待メール (admin_create_user 経由) の本文中に埋め込むログイン URL。
# CloudFront ドメインを直接参照すると aws_cognito_user_pool → CloudFront →
# aws_cognito_user_pool_domain → aws_cognito_user_pool の循環が起きるため変数化する。
# 本番は CloudFront ドメイン (例: https://d3dz1e2hexhvbr.cloudfront.net/login) を
# terraform.tfvars で渡す想定。独自ドメイン適用後は差し替えれば良い。
variable "app_login_url" {
  description = "Login URL shown in Cognito invite emails (e.g. https://<cloudfront>/login)"
  type        = string
}

variable "central_authz_url" {
  description = <<-EOT
    共通認証基盤（auth-console）の URL。

    空なら中央を使わず、従来どおり Django の is_superuser だけで
    管理者判定する。公開版や検証環境ではこのままでよい。
  EOT
  type        = string
  default     = ""
}

variable "shared_lambda_security_group_id" {
  description = <<-EOT
    この RDS への接続を許可する共有 Lambda セキュリティグループ。

    fair-value-calculator の RDS は task-scope など他の個人ツールと
    共有しているため、それらの Lambda からの 3306 を通す必要がある。
    **この設定が無いと task-scope が DB に繋がらなくなる。**

    空なら追加しない（公開版・検証環境ではこのままでよい）。
  EOT
  type        = string
  default     = ""
}

variable "enable_optional_schedules" {
  description = <<-EOT
    必須ではない定期同期を有効にするか。

    配当・信用残・為替・ニュース・寄り付き株価など 9 本が対象。
    コスト削減のため既定で停止している（手で止めた状態を tf に反映）。

    **true にすると 9 本が一斉に動き出し、Lambda 実行と外部 API 呼び出しが
    増える。** 必要になったときだけ有効にする。
  EOT
  type        = bool
  default     = false
}

# -----------------------------------------------------------------------------
# Cognito（cognito-auth-service に統合済み）
# -----------------------------------------------------------------------------
#
# 値は Akinori901/cognito-auth-service リポジトリの `terraform output` から取得する:
#   user_pool_id / fvc_web_client_id / fvc_gpt_client_id / domain_prefix

variable "cognito_user_pool_id" {
  description = "認証に使う Cognito User Pool ID（cognito-auth-service）"
  type        = string
  default     = ""
}

variable "cognito_web_client_id" {
  description = "Web（SPA）用の App Client ID"
  type        = string
  default     = ""
}

variable "cognito_gpt_client_id" {
  description = "Custom GPT 用の App Client ID"
  type        = string
  default     = ""
}

variable "cognito_domain_prefix" {
  description = "Hosted UI のドメイン prefix"
  type        = string
  default     = ""
}
