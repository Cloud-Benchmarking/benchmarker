resource "digitalocean_ssh_key" "ssh_key" {
  name = format("benchmark-key-%s", var.label_scratch)
  public_key = var.public_key
}
resource "digitalocean_droplet" "benchmark" {
  image = "ubuntu-20-10-x64"
  name = format("benchmark-%s", var.label_scratch)
  region = var.region
  size = "s-1vcpu-1gb"
  monitoring = true
  private_networking = var.enable_private_networking

  ssh_keys = [
    digitalocean_ssh_key.ssh_key.id]
  //*/
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
    host = self.ipv4_address
  }

  provisioner "file" {
    source      = var.provision_script_path
    destination = "/tmp/provision-benchmark-node.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/provision-benchmark-node.sh",
      "/tmp/provision-benchmark-node.sh benchmark-${var.label_scratch}"
    ]
  }
}