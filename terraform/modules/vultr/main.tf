resource "vultr_ssh_key" "ssh_key" {
  name = "benchmark-key"
  ssh_key = chomp(var.public_key)
}

resource "vultr_instance" "benchmark" {
  label = format("benchmark-%s", var.label_scratch)
  region = var.region

  enable_private_network = var.enable_private_networking
  # https://api.vultr.com/v2/plans
  plan = "vc2-1c-1gb" # 1024 MB RAM,25 GB SSD,1.00 TB BW
  # https://api.vultr.com/v2/os
  os_id = "413" # ubuntu 20.10 x64

//  tag = "tag"

  ssh_key_ids = [
    vultr_ssh_key.ssh_key.id]

//  tags = [
//    //    "benchmark",
//    //    "linode",
//    //    "iperf",
//    //    "netperf",
//    var.region,
//    "workspace:${terraform.workspace}",
//    "created:${timestamp()}"
//  ]

  connection {
    type = "ssh"
    user = "root"
    private_key = var.private_key
    host = self.main_ip
  }

  provisioner "file" {
    source      = var.provision_script_path
    destination = "/tmp/provision-benchmark-node.sh"
  }

  provisioner "file" {
    source      = "${path.module}/private-networking.sh"
    destination = "/tmp/private-networking.sh"
  }

  provisioner "file" {
    source      = "${path.module}/10-ens7.yaml"
    destination = "/etc/netplan/10-ens7.yaml"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/private-networking.sh",
      "/tmp/private-networking.sh ${var.enable_private_networking} ${self.internal_ip}",
    ]
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/provision-benchmark-node.sh",
      "/tmp/provision-benchmark-node.sh benchmark-${var.label_scratch}"
    ]
  }
}