output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (the public URL)"
  value       = aws_cloudfront_distribution.main.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (for cache invalidation)"
  value       = aws_cloudfront_distribution.main.id
}

output "api_gateway_endpoint" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.backend.repository_url
}

output "lambda_api_function_name" {
  description = "Lambda API function name"
  value       = aws_lambda_function.api.function_name
}

output "lambda_worker_function_name" {
  description = "Lambda worker function name"
  value       = aws_lambda_function.worker.function_name
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.main.endpoint
}

output "s3_bucket_name" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.frontend.bucket
}

output "github_actions_access_key_id" {
  description = "Access key ID for GitHub Actions"
  value       = aws_iam_access_key.github_actions.id
  sensitive   = true
}

output "github_actions_secret_access_key" {
  description = "Secret access key for GitHub Actions"
  value       = aws_iam_access_key.github_actions.secret
  sensitive   = true
}

# -----------------------------------------------------------------------------
# Cognito
# -----------------------------------------------------------------------------

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID (for backend JWT verification)"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_web_client_id" {
  description = "Cognito App Client ID (Web / SPA, public client)"
  value       = aws_cognito_user_pool_client.web.id
}

output "cognito_gpt_client_id" {
  description = "Cognito App Client ID (Custom GPT, confidential client)"
  value       = aws_cognito_user_pool_client.gpt.id
}

output "cognito_gpt_client_secret" {
  description = "Cognito App Client secret (Custom GPT) — to be set on the GPT side"
  value       = aws_cognito_user_pool_client.gpt.client_secret
  sensitive   = true
}

output "cognito_domain" {
  description = "Cognito Hosted UI domain (e.g. fvc-prod.auth.ap-northeast-1.amazoncognito.com)"
  value       = "${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "cognito_authorization_url" {
  description = "Cognito Authorization endpoint (for Custom GPT OAuth setup)"
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com/oauth2/authorize"
}

output "cognito_token_url" {
  description = "Cognito Token endpoint (for Custom GPT OAuth setup)"
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com/oauth2/token"
}

output "cognito_google_redirect_uri" {
  description = "Google Cloud Console に登録する Cognito 側の Authorized redirect URI"
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com/oauth2/idpresponse"
}
