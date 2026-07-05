# =============================================================================
# Cognito User Pool — OAuth 認証基盤
# =============================================================================
#
# Web (SPA) と Custom GPT (Actions) の両方の認証経路を 1 つの User Pool で集約する。
# Claude Desktop / Gemini CLI 等の MCP 機械クライアントは別系統の API キー認証を継続利用する。
#
# 設計書: docs/design/cognito-oauth-migration.md §5, §11
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# User Pool
# -----------------------------------------------------------------------------

resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-user-pool"

  # email でサインイン
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_uppercase = true
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # signup は admin 招待のみ。GPT Store 公開時は別 App Client で許可する
  admin_create_user_config {
    allow_admin_create_user_only = true

    # 招待メール (admin_create_user 実行時に Cognito から送信される) の文面。
    # {username} = email、{####} = Cognito 自動生成の仮パスワード。両プレースホルダ必須。
    # 送信元は Cognito デフォルト (no-reply@verificationemail.com)。
    invite_message_template {
      email_subject = "【Fair Value Calculator】アカウント招待 / Your account invitation"
      email_message = <<-EOT
        Fair Value Calculator をご利用いただきありがとうございます。
        管理者があなたのアカウントを作成しました。下記の情報で初回ログインを行ってください。

          ユーザー名 (Username) : {username}
          仮パスワード (Temporary password) : {####}

        ログイン URL :
          ${var.app_login_url}

        初回ログイン後、パスワードの変更を求められます。
        仮パスワードは一定期間で失効しますので、お早めにログインしてください。

        このメールに心当たりがない場合は、本メールを破棄してください。
        ご不明な点は管理者までお問い合わせください。

        --- English ---

        Welcome to Fair Value Calculator.
        An administrator has created an account for you. Please sign in for the first time using the credentials below.

          Username           : {username}
          Temporary password : {####}

        Sign-in URL:
          ${var.app_login_url}

        You will be asked to change your password on first sign-in.
        The temporary password expires after a limited period, so please sign in soon.

        If you did not expect this email, please simply discard it.
        For any questions, contact your administrator.

        -- Fair Value Calculator
      EOT
      sms_message   = "Fair Value Calculator: username {username}, temp password {####}"
    }
  }

  deletion_protection = "ACTIVE"

  schema {
    name                     = "name"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  tags = {
    Name = "${var.project_name}-user-pool"
  }
}

# -----------------------------------------------------------------------------
# User Pool Domain (Cognito prefix domain)
# -----------------------------------------------------------------------------

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.project_name}-prod"
  user_pool_id = aws_cognito_user_pool.main.id
}

# -----------------------------------------------------------------------------
# Identity Provider: Google
# -----------------------------------------------------------------------------
#
# 事前に Google Cloud Console で OAuth 2.0 Client ID を作成しておく:
#   - 種類: ウェブアプリケーション
#   - 承認済みリダイレクト URI:
#     https://${var.project_name}-prod.auth.${var.aws_region}.amazoncognito.com/oauth2/idpresponse
#
# 取得した client_id / client_secret を terraform.tfvars に投入:
#   google_oauth_client_id     = "xxx.apps.googleusercontent.com"
#   google_oauth_client_secret = "GOCSPX-xxx"

resource "aws_cognito_identity_provider" "google" {
  user_pool_id  = aws_cognito_user_pool.main.id
  provider_name = "Google"
  provider_type = "Google"

  # provider_details:
  # - 認証情報 (client_id / client_secret) と利用スコープ (authorize_scopes) は
  #   Google Cloud Console で取得した値を terraform.tfvars 経由で投入する。
  # - attributes_url / authorize_url / oidc_issuer / token_url 等は Cognito が
  #   Google プロバイダタイプ用に自動補完する固定値。terraform で明示しないと
  #   plan のたびに「自動補完値を null にしようとする」drift が出てしまうため、
  #   AWS Console / state で確認できる値をそのまま固定する。
  # - ここに記載した URL は Google OAuth 2.0 の公開エンドポイントで、機密性なし。
  provider_details = {
    client_id                     = var.google_oauth_client_id
    client_secret                 = var.google_oauth_client_secret
    authorize_scopes              = "openid email profile"
    attributes_url                = "https://people.googleapis.com/v1/people/me?personFields="
    attributes_url_add_attributes = "true"
    authorize_url                 = "https://accounts.google.com/o/oauth2/v2/auth"
    oidc_issuer                   = "https://accounts.google.com"
    token_request_method          = "POST"
    token_url                     = "https://www.googleapis.com/oauth2/v4/token"
  }

  attribute_mapping = {
    email          = "email"
    email_verified = "email_verified"
    name           = "name"
    username       = "sub"
  }
}

# -----------------------------------------------------------------------------
# App Client A: Web (SPA, PKCE, public client)
# -----------------------------------------------------------------------------

resource "aws_cognito_user_pool_client" "web" {
  name         = "${var.project_name}-web-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = false # SPA なので client_secret は持たない (PKCE で守る)

  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "profile", "email"]
  supported_identity_providers = [
    "COGNITO",
    aws_cognito_identity_provider.google.provider_name,
  ]

  callback_urls = [
    "http://localhost:8888/auth/callback",
    "https://${aws_cloudfront_distribution.main.domain_name}/auth/callback",
  ]
  logout_urls = [
    "http://localhost:8888/login",
    "https://${aws_cloudfront_distribution.main.domain_name}/login",
  ]

  prevent_user_existence_errors = "ENABLED"

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 30
  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }
}

# -----------------------------------------------------------------------------
# App Client B: Custom GPT (confidential client, has client_secret)
# -----------------------------------------------------------------------------
#
# Custom GPT 作成後、GPT が発行する Callback URL を Console で追加する必要がある。
# 例: https://chat.openai.com/aip/g-xxxxxxxxxx/oauth/callback
# lifecycle.ignore_changes で Terraform 管理外とする。

resource "aws_cognito_user_pool_client" "gpt" {
  name         = "${var.project_name}-gpt-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = true # Custom GPT は client_secret を要求する

  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "profile", "email"]
  supported_identity_providers = [
    "COGNITO",
    aws_cognito_identity_provider.google.provider_name,
  ]

  callback_urls = [
    # GPT 作成後に Console で実 URL に置き換える。初回 apply 用のプレースホルダ。
    "https://chat.openai.com/aip/PLACEHOLDER/oauth/callback",
  ]

  prevent_user_existence_errors = "ENABLED"

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 30
  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  lifecycle {
    # Console で GPT の callback URL を追加することを許容する
    ignore_changes = [callback_urls]
  }
}
