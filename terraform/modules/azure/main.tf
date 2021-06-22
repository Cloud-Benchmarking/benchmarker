locals {
  vm_username = "azureroot"
}
resource "azurerm_resource_group" "benchmark-resource-group" {
  name = format("benchmark-rg-%s", var.label_scratch)
  location = var.region

  tags = {
    environment = "Benchmarking"
  }
}
resource "azurerm_virtual_network" "benchmark-virt-net" {
  name = format("benchmark-network-%s", var.label_scratch)
  address_space = [
    "10.0.0.0/16"]
  location = azurerm_resource_group.benchmark-resource-group.location
  resource_group_name = azurerm_resource_group.benchmark-resource-group.name
}
resource "azurerm_subnet" "benchmark-subnet" {
  name = format("benchmark-subnet-%s", var.label_scratch)
  resource_group_name = azurerm_resource_group.benchmark-resource-group.name
  virtual_network_name = azurerm_virtual_network.benchmark-virt-net.name
  address_prefixes = [
    "10.0.2.0/24"]
}
resource "azurerm_public_ip" "benchmark-public-ip" {
  name = format("benchmark-public-ip-%s", var.label_scratch)
  location = var.region
  resource_group_name = azurerm_resource_group.benchmark-resource-group.name
  allocation_method = "Dynamic"

  tags = {
    environment = format("benchmark-%s", var.label_scratch)
  }
}
resource "azurerm_network_interface" "benchmark-nic" {
  name = format("benchmark-nic-%s", var.label_scratch)
  location = var.region
  resource_group_name = format("benchmark-rg-%s", var.label_scratch)

  ip_configuration {
    name = "internal"
    subnet_id = azurerm_subnet.benchmark-subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id = azurerm_public_ip.benchmark-public-ip.id
  }

  tags = {
    environment = format("benchmark-%s", var.label_scratch)
  }
}

resource "azurerm_linux_virtual_machine" "benchmark" {
  admin_username = local.vm_username
  location = var.region
  name = format("benchmark-%s", var.label_scratch)
  computer_name = format("benchmark-%s", var.label_scratch)
  network_interface_ids = [
    azurerm_network_interface.benchmark-nic.id
  ]

  admin_ssh_key {
    username = local.vm_username
    public_key = chomp(var.public_key)
  }

  resource_group_name = "cloud-benchmarking-dev"
  size = "Standard_B1s"
  os_disk {
    name = format("osdisk-%s", var.label_scratch)
    caching = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer = "0001-com-ubuntu-server-groovy"
    sku = "20_10-gen2"
    version = "latest"
  }

    connection {
      type = "ssh"
      user = "azureroot"
      private_key = var.private_key
      host = self.public_ip_address
    }

    provisioner "file" {
      source = var.provision_script_path
      destination = "~/provision-benchmark-node.sh"
    }

    provisioner "remote-exec" {
      inline = [
        "chmod +x ~/provision-benchmark-node.sh",
        "sudo ~/provision-benchmark-node.sh benchmark-${var.label_scratch}"
      ]
    }
}