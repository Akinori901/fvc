# =============================================================================
# IAM — Lambda 実行ロール + GitHub Actions デプロイユーザー
# =============================================================================

# -----------------------------------------------------------------------------
# Lambda 実行ロール
# -----------------------------------------------------------------------------

resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = { Name = "${var.project_name}-lambda-role" }
}

# CloudWatch Logs 書き込み権限
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# VPC 内 ENI 管理権限
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# SSM Parameter Store 読取権限（管理者ロール専用 OpenAI キー）
resource "aws_iam_role_policy" "lambda_ssm_read" {
  name = "${var.project_name}-lambda-ssm-read"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadAdminSecrets"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
        ]
        Resource = aws_ssm_parameter.openai_admin_api_key.arn
      },
      # SecureString の復号に必要（デフォルト alias/aws/ssm KMS キーを使用）
      {
        Sid      = "DecryptSsmSecureString"
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "ssm.${var.aws_region}.amazonaws.com"
          }
        }
      },
    ]
  })
}

# Cognito User Pool 管理 API 読取権限 (Admin 管理画面で list_users を叩く)
resource "aws_iam_role_policy" "lambda_cognito_admin" {
  name = "${var.project_name}-lambda-cognito-admin"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CognitoAdminReadWrite"
        Effect = "Allow"
        Action = [
          "cognito-idp:ListUsers",
          "cognito-idp:AdminGetUser",
          "cognito-idp:AdminDisableUser",
          "cognito-idp:AdminEnableUser",
          "cognito-idp:AdminDeleteUser",
        ]
        Resource = aws_cognito_user_pool.main.arn
      },
    ]
  })
}

# -----------------------------------------------------------------------------
# GitHub Actions デプロイ用 IAM ユーザー
# -----------------------------------------------------------------------------

resource "aws_iam_user" "github_actions" {
  name = "${var.project_name}-github-actions"

  tags = { Name = "${var.project_name}-github-actions" }
}

resource "aws_iam_user_policy" "github_actions" {
  name = "${var.project_name}-github-actions-deploy"
  user = aws_iam_user.github_actions.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ECRAuth"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Sid    = "ECRPush"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
        ]
        Resource = aws_ecr_repository.backend.arn
      },
      {
        Sid    = "LambdaUpdate"
        Effect = "Allow"
        Action = [
          "lambda:UpdateFunctionCode",
          "lambda:GetFunction",
          "lambda:GetFunctionConfiguration",
          "lambda:InvokeFunction",
        ]
        Resource = [
          aws_lambda_function.api.arn,
          aws_lambda_function.worker.arn,
        ]
      },
      {
        Sid    = "S3Deploy"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket",
        ]
        Resource = [
          aws_s3_bucket.frontend.arn,
          "${aws_s3_bucket.frontend.arn}/*",
        ]
      },
      {
        Sid    = "CloudFrontInvalidation"
        Effect = "Allow"
        Action = [
          "cloudfront:CreateInvalidation",
          "cloudfront:GetInvalidation",
        ]
        Resource = aws_cloudfront_distribution.main.arn
      },
    ]
  })
}

# GitHub Actions 用アクセスキー
resource "aws_iam_access_key" "github_actions" {
  user = aws_iam_user.github_actions.name
}
