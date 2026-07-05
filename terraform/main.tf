provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "fair-value-calculator"
      Environment = "production"
      ManagedBy   = "terraform"
    }
  }
}
