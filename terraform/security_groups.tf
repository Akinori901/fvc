# =============================================================================
# セキュリティグループ
# =============================================================================

# Lambda 用
resource "aws_security_group" "lambda" {
  name_prefix = "${var.project_name}-lambda-"
  description = "Security group for Lambda function"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound (NAT Gateway, RDS)"
  }

  tags = { Name = "${var.project_name}-lambda-sg" }
}

# NAT Instance 用
resource "aws_security_group" "nat_instance" {
  name_prefix = "${var.project_name}-nat-"
  description = "Security group for NAT Instance"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["10.0.10.0/24", "10.0.11.0/24"]
    description = "All traffic from private subnets"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = { Name = "${var.project_name}-nat-sg" }
}

# RDS 用
resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-rds-"
  description = "Security group for RDS MySQL"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
    description     = "MySQL from Lambda only"
  }

  # この RDS は task-scope など他の個人ツールと共有している。
  #
  # **この 1 本を消すと task-scope の本番が DB に繋がらなくなる。**
  # 手で追加されていて tf に無かったため、plan のたびに削除差分として
  # 現れていた（apply すれば即障害になる状態だった）。
  #
  # shared-lambda-sg は fair-value-calculator の管理外なので、
  # ID を変数で受け取る。空なら追加しない（公開版・検証環境向け）。
  dynamic "ingress" {
    for_each = var.shared_lambda_security_group_id != "" ? [1] : []
    content {
      from_port       = 3306
      to_port         = 3306
      protocol        = "tcp"
      security_groups = [var.shared_lambda_security_group_id]
      # 実物の description が空のため合わせる。文字列を入れると
      # plan に毎回差分が出る（意味は上のコメントで担保する）。
      description = ""
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-rds-sg" }
}
