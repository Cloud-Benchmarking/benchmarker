terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
    }
    local = {
      source = "hashicorp/local"
    }
    tls = {
      source = "hashicorp/tls"
    }
    linode = {
      source = "linode/linode"
    }
    vultr = {
      source = "vultr/vultr"
    }
    ovh = {
      source = "ovh/ovh"
    }
  }
  required_version = ">= 0.13"
}
