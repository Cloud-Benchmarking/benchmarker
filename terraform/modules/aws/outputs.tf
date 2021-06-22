output "ip_address" {
  value = aws_instance.benchmark.public_ip
}
output "private_ip_address" {
  value = aws_instance.benchmark.private_ip
}
output "region" {
  value = aws_instance.benchmark.availability_zone
}
output "provider" {
  value = "aws"
}