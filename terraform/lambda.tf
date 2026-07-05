# =============================================================================
# Lambda — API + Worker
# =============================================================================

# -----------------------------------------------------------------------------
# API Lambda（HTTP リクエスト処理）
# -----------------------------------------------------------------------------

resource "aws_lambda_function" "api" {
  function_name = "${var.project_name}-api"
  role          = aws_iam_role.lambda_execution.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.backend.repository_url}:latest"

  memory_size = 1536
  timeout     = 90

  image_config {
    command = ["config.asgi.handler"]
  }

  environment {
    variables = {
      DJANGO_SETTINGS_MODULE         = "config.settings.production"
      SECRET_KEY                     = var.django_secret_key
      ALLOWED_HOSTS                  = "*"
      DATABASE_HOST                  = aws_db_instance.main.address
      DATABASE_PORT                  = tostring(aws_db_instance.main.port)
      DATABASE_NAME                  = var.db_name
      DATABASE_USER                  = var.db_username
      DATABASE_PASSWORD              = var.db_password
      CORS_ALLOWED_ORIGINS           = "*"
      AWS_STORAGE_BUCKET_NAME        = var.s3_bucket_name
      OPENAI_ADMIN_KEY_SSM_PARAMETER = aws_ssm_parameter.openai_admin_api_key.name
      # Cognito (認証)
      COGNITO_USER_POOL_ID  = aws_cognito_user_pool.main.id
      COGNITO_REGION        = var.aws_region
      COGNITO_WEB_CLIENT_ID = aws_cognito_user_pool_client.web.id
      COGNITO_GPT_CLIENT_ID = aws_cognito_user_pool_client.gpt.id
      COGNITO_DOMAIN_PREFIX = aws_cognito_user_pool_domain.main.domain
      # MCP Streamable HTTP (/mcp) は incident_mcp_lifespan_2026_05_19 以降無効化。
      # 2026-05-24 に再有効化を試したが lifespan failure で /mcp/ が 500 になり revert。
      # 根本対応 (FastMCP の lifespan を Lambda の cold/warm start に適合) が必要。
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_c.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy_attachment.lambda_vpc,
    aws_iam_role_policy.lambda_ssm_read,
    aws_cloudwatch_log_group.lambda_api,
  ]

  tags = { Name = "${var.project_name}-api-lambda" }
}

# -----------------------------------------------------------------------------
# Worker Lambda（管理コマンド: migrate, sync 等）
# -----------------------------------------------------------------------------

resource "aws_lambda_function" "worker" {
  function_name = "${var.project_name}-worker"
  role          = aws_iam_role.lambda_execution.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.backend.repository_url}:latest"

  memory_size = 2048
  timeout     = 900

  image_config {
    command = ["config.management_handler.handler"]
  }

  environment {
    variables = {
      DJANGO_SETTINGS_MODULE  = "config.settings.production"
      SECRET_KEY              = var.django_secret_key
      ALLOWED_HOSTS           = "*"
      DATABASE_HOST           = aws_db_instance.main.address
      DATABASE_PORT           = tostring(aws_db_instance.main.port)
      DATABASE_NAME           = var.db_name
      DATABASE_USER           = var.db_username
      DATABASE_PASSWORD       = var.db_password
      AWS_STORAGE_BUCKET_NAME = var.s3_bucket_name
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_c.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy_attachment.lambda_vpc,
    aws_cloudwatch_log_group.lambda_worker,
  ]

  tags = { Name = "${var.project_name}-worker-lambda" }
}

# -----------------------------------------------------------------------------
# CloudWatch Log Groups
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "lambda_api" {
  name              = "/aws/lambda/${var.project_name}-api"
  retention_in_days = 14

  tags = { Name = "${var.project_name}-api-logs" }
}

resource "aws_cloudwatch_log_group" "lambda_worker" {
  name              = "/aws/lambda/${var.project_name}-worker"
  retention_in_days = 14

  tags = { Name = "${var.project_name}-worker-logs" }
}
