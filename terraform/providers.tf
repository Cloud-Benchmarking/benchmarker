provider "digitalocean" {
  token = var.do_api_token
  spaces_access_id = var.do_space_key
  spaces_secret_key = var.do_space_secret
}

provider "linode" {
  token = var.linode_api_token
}

provider "vultr" {
  api_key = var.vultr_api_token
}
provider "ovh" {
  endpoint = "ovh-eu"
  application_key = var.ovh_application_key
  application_secret = var.ovh_application_secret
}
provider "azurerm" {
  features {}
  client_id = var.azure_client_id
  client_secret = var.azure_client_secret
  subscription_id = var.azure_subscription_id
  tenant_id = var.azure_tenant_id
}

provider "google" {
  project = ""
  credentials = file(var.gcp_credential_file)
}

// aws provider configured within the module
// due to needing a region