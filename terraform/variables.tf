variable "do_api_token" {}
variable "do_space_key" {}
variable "do_space_secret" {}
variable "linode_api_token" {}
variable "vultr_api_token" {}
variable "ovh_application_key" {}
variable "ovh_application_secret" {}
variable "hetzner_api_token" {}
variable "azure_client_id" {}
variable "azure_client_secret" {}
variable "azure_subscription_id" {}
variable "azure_tenant_id" {}

variable "aws_access_key" {}
variable "aws_secret_access_key" {}

variable "gcp_credential_file" {}

# benchmark specific
variable "src_region" {
  type = string
}
variable "dst_region" {
  type = string
}
variable "src_zone" {
  type = string
}
variable "dst_zone" {
  type = string
}
variable "uuid_partial" {
  type = string
}
variable "enable_private_networking" {
  type = bool
}