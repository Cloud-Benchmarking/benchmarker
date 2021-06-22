resource "linode_sshkey" "ssh_key" {
  label = "benchmark-key"
  ssh_key = chomp(var.public_key)
}
resource "linode_instance" "benchmark" {
  image = "linode/ubuntu20.10"
  label = format("benchmark-%s", var.label_scratch)
  region = var.region
  type = "g6-nanode-1"
  private_ip = var.enable_private_networking

  authorized_keys = [
    linode_sshkey.ssh_key.ssh_key]

  tags = [
//    "benchmark",
//    "linode",
//    "iperf",
//    "netperf",
    var.region,
    "workspace:${terraform.workspace}",
    "created:${timestamp()}"
  ]

  connection {
    type = "ssh"
    user = "root"
    private_key = var.private_key
    host = self.ip_address
  }

  provisioner "file" {
    source      = var.provision_script_path
    destination = "~/provision-benchmark-node.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x ~/provision-benchmark-node.sh",
      "~/provision-benchmark-node.sh benchmark-${var.label_scratch}"
    ]
  }
}