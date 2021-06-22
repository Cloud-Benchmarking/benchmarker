provider "aws" {
  region = var.region
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
}
resource "aws_key_pair" "benchmark_key" {
  key_name = format("benchmark-%s-key", var.label_scratch)
  public_key = var.public_key
}
data "aws_ami" "ubuntu" {
  # ami-04586159bd0512348
  most_recent = true

  filter {
    name = "name"
    values = [
      "ubuntu/images/hvm-ssd/ubuntu-groovy-20.10-amd64-server-*"]
  }

  filter {
    name = "virtualization-type"
    values = [
      "hvm"]
  }

  owners = [
    "099720109477"]
  # Canonical
}

resource "aws_security_group" "benchmark_sg" {
  name = format("benchmark-%s-sg", var.label_scratch)

  ingress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = [
      "0.0.0.0/0"]
  }

  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = [
      "0.0.0.0/0"]
  }
}
resource "aws_instance" "benchmark" {
  # ubuntu 20.10 amd64 provided by Canonical
  ami = data.aws_ami.ubuntu.id
  instance_type = "t2.micro"
  key_name = aws_key_pair.benchmark_key.key_name
  availability_zone = var.zone

  //  availability_zone = "us-east-1"
  vpc_security_group_ids = [
    aws_security_group.benchmark_sg.id
  ]

  tags = {
    Name = format("benchmark-%s", var.label_scratch)
  }

  connection {
    type = "ssh"
    user = "ubuntu"
    private_key = var.private_key
    # might need an internet gateway, route table, and route-association
    # https://stackoverflow.com/questions/55878755/terraform-fails-remote-exec-aws-ec2
    host = self.public_ip
  }

  provisioner "file" {
    source = var.provision_script_path
    destination = "/tmp/provision-benchmark-node.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/provision-benchmark-node.sh",
      "sudo /tmp/provision-benchmark-node.sh benchmark-testing"
    ]
  }
}