terraform {
  required_version = ">= 1.5.7"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.47"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_client_config" "default" {}
