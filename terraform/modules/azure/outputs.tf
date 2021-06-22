output "ip_address" {
  value = azurerm_linux_virtual_machine.benchmark.public_ip_address
}
output "private_ip_address" {
  value = azurerm_linux_virtual_machine.benchmark.private_ip_address
}
output "region" {
  value = azurerm_linux_virtual_machine.benchmark.location
}
output "provider" {
  value = "azure"
}