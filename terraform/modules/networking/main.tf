resource "google_compute_network" "main" {
  name                    = "precision-genomics-vpc"
  project                 = var.project_id
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "main" {
  name          = "precision-genomics-subnet"
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.main.id
  ip_cidr_range = "10.0.0.0/20"
}

resource "google_compute_global_address" "private_ip" {
  name          = "precision-genomics-private-ip"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main.id
}

resource "google_service_networking_connection" "private_vpc" {
  network                 = google_compute_network.main.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip.name]
}

resource "google_vpc_access_connector" "main" {
  name          = "precision-genomics-vpc"
  project       = var.project_id
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.main.name
}

variable "project_id" { type = string }
variable "region" { type = string }

output "network_id" { value = google_compute_network.main.id }
output "subnet_id" { value = google_compute_subnetwork.main.id }
output "vpc_connector_id" { value = google_vpc_access_connector.main.id }
output "vpc_connector_cidr" { value = google_vpc_access_connector.main.ip_cidr_range }
