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
