# =============================================================================
# NAT Instance（t4g.nano — NAT Gateway 代替でコスト削減）
#
# NAT Gateway: ~$33/月（固定） + データ転送料
# NAT Instance (t4g.nano): ~$3/月 + データ転送料
# =============================================================================

# 最新の Amazon Linux 2023 ARM AMI を取得
data "aws_ami" "al2023_arm" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023*-kernel-6.1-arm64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["arm64"]
  }
}

# NAT Instance 用 EIP
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = { Name = "${var.project_name}-nat-eip" }
}

resource "aws_eip_association" "nat" {
  instance_id   = aws_instance.nat.id
  allocation_id = aws_eip.nat.id
}

# NAT Instance
#
# AMI は `data.aws_ami.al2023_arm` で最新の Amazon Linux 2023 を取得しているが、
# AWS が新 AMI を公開するたびに plan 上で `forces replacement` が発生し、
# 毎回 NAT 再作成 (= Lambda → 外部 API のダウンタイム数分) が起きてしまう。
# `lifecycle.ignore_changes = [ami]` で AMI 変更を terraform に検知させず、
# 既存インスタンスを維持する。意図的に AMI を更新したいときは:
#   terraform taint aws_instance.nat
# または terraform.tfstate から該当リソースを削除して再 apply する。
resource "aws_instance" "nat" {
  ami                    = data.aws_ami.al2023_arm.id
  instance_type          = "t4g.nano"
  subnet_id              = aws_subnet.public_a.id
  vpc_security_group_ids = [aws_security_group.nat_instance.id]
  source_dest_check      = false

  user_data = <<-EOF
    #!/bin/bash
    # Enable IP forwarding
    echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
    sysctl -p

    # Configure iptables for NAT (MASQUERADE)
    yum install -y iptables-services
    iptables -t nat -A POSTROUTING -o ens5 -s 10.0.0.0/16 -j MASQUERADE
    iptables -A FORWARD -i ens5 -o ens5 -m state --state RELATED,ESTABLISHED -j ACCEPT
    iptables -A FORWARD -i ens5 -o ens5 -j ACCEPT
    service iptables save
    systemctl enable iptables
  EOF

  tags = { Name = "${var.project_name}-nat-instance" }

  lifecycle {
    ignore_changes = [ami]
  }

  depends_on = [aws_internet_gateway.main]
}
