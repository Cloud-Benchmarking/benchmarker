resource "google_compute_firewall" "benchmark_firewall" {
 name    = format("benchmark-%s-firewall", var.label_scratch)
// network = google_compute_network.benchmark_network.name
  network = "default"

 allow {
   protocol = "tcp"
   ports    = ["20000"]
 }
  allow {
    protocol = "icmp"
  }
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  allow {
    protocol = "udp"
    ports    = ["33434-33600"]
  }
}

// A single Compute Engine instance
resource "google_compute_instance" "benchmark" {
  name = format("benchmark-%s", var.label_scratch)

  # custom-NUMBER_OF_CPUS-AMOUNT_OF_MEMORY_MB == 1vCPU/1GB
  machine_type = "custom-1-1024"
  zone = var.zone
  can_ip_forward = true

  # no other cloud provider allows specifying a CPU platform
  # Skylake is newest CPU available in every region
  # so this will be used.
  min_cpu_platform = "Intel Skylake"

  boot_disk {
    initialize_params {
      image = "ubuntu-2010-groovy-v20210119a"
    }
  }

  metadata = {
    ssh-keys = "root:${chomp(var.public_key)}"
  }

  network_interface {
//    network = google_compute_network.benchmark_network.self_link
//    network_ip = google_compute_global_address.benchmark_internal_ip.address
    network = "default"
    access_config {
      network_tier = "STANDARD"
      // Include this section to give the VM an external ip address
    }
  }

  connection {
    type = "ssh"
    user = "root"
    private_key = var.private_key
    host = self.network_interface.0.access_config.0.nat_ip
  }

  // google_compute_instance has an attribute `metadata_startup_script`
  // but we will use file && remote-exec provisioner to be consistent with
  // the other modules
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