output "ip_address" {
  value = digitalocean_droplet.benchmark.ipv4_address
}
output "private_ip_address" {
  value = digitalocean_droplet.benchmark.ipv4_address_private
}
output "region" {
  value = digitalocean_droplet.benchmark.region
}
output "provider" {
  value = "digitalocean"
}