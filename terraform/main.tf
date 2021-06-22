resource "tls_private_key" "ssh" {
  count = 2
  algorithm = "RSA"
  rsa_bits = 4096
}

resource "local_file" "ssh_private_key" {
  count = length(tls_private_key.ssh)
  content = tls_private_key.ssh[count.index].private_key_pem
  filename = "${path.module}/id_rsa-${count.index}"
  file_permission = "600"
}
resource "local_file" "ssh_public_key" {
  count = length(tls_private_key.ssh)
  content = tls_private_key.ssh[count.index].public_key_openssh
  filename = "${path.module}/id_rsa-${count.index}.pub"
  file_permission = "600"
}

module "src" {
  source = "./modules/null"
  # aws provider requires region, but we only know that at run-time
  # so do the stupid thing and pass creds in through the module
  aws_access_key = var.aws_access_key
  aws_secret_key = var.aws_secret_access_key

  region = var.src_region
  zone = var.src_zone
  public_key = tls_private_key.ssh[0].public_key_openssh
  private_key = tls_private_key.ssh[0].private_key_pem
  label_scratch = "${var.uuid_partial}-src"
  provision_script_path = "${path.module}/provision-benchmark-node.sh"
  enable_private_networking = var.enable_private_networking
}

module "dst" {
  source = "./modules/null"
  # aws provider requires region, but we only know that at run-time
  # so do the stupid thing and pass creds in through the module
  aws_access_key = var.aws_access_key
  aws_secret_key = var.aws_secret_access_key

  region = var.dst_region
  zone = var.dst_zone
  public_key = tls_private_key.ssh[1].public_key_openssh
  private_key = tls_private_key.ssh[1].private_key_pem
  label_scratch = "${var.uuid_partial}-dst"
  provision_script_path = "${path.module}/provision-benchmark-node.sh"
  enable_private_networking = var.enable_private_networking
}

output "benchmark_targets" {
  value = {
    src = {
      ip_address = module.src.ip_address,
      private_ip_address = module.src.private_ip_address
      region = module.src.region,
      zone = var.src_zone,
      provider = module.src.provider,
      src_dst = "src",
      ssh_private_key = local_file.ssh_private_key[0].filename,
      uuid_partial = var.uuid_partial,
    },
    dst = {
      ip_address = module.dst.ip_address
      private_ip_address = module.dst.private_ip_address
      region = module.dst.region,
      zone = var.dst_zone,
      provider = module.dst.provider,
      src_dst = "dst"
      ssh_private_key = local_file.ssh_private_key[1].filename
      uuid_partial = var.uuid_partial
    }
  }
}