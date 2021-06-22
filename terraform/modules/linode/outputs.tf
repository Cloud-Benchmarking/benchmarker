output "ip_address" {
  value = linode_instance.benchmark.ip_address
}
output "private_ip_address" {
  value = linode_instance.benchmark.private_ip_address
}
output "region" {
  value = linode_instance.benchmark.region
}
output "provider" {
  value = "linode"
}