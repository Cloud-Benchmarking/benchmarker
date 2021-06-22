output "ip_address" {
  value = vultr_instance.benchmark.main_ip
}
output "private_ip_address" {
  value = vultr_instance.benchmark.internal_ip
}
output "region" {
  value = vultr_instance.benchmark.region
}
output "provider" {
  value = "vultr"
}