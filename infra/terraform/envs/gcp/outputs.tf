output "cluster_name" {
  description = "GKE cluster name."
  value       = module.gke.name
}

output "cluster_endpoint" {
  description = "GKE API server endpoint (without scheme)."
  value       = module.gke.endpoint
}

output "cluster_ca_certificate" {
  description = "Base64 encoded CA certificate for the GKE cluster."
  value       = module.gke.ca_certificate
  sensitive   = true
}

output "identity_namespace" {
  description = "Workload Identity pool (format: [project_id].svc.id.goog)."
  value       = module.gke.identity_namespace
}

output "service_account" {
  description = "Email of the service account used by GKE worker nodes."
  value       = module.gke.service_account
}

output "artifact_registry_url" {
  description = "Artifact Registry repository URL for Docker images."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/moiraweave"
}

output "kubernetes_provider_config" {
  description = "HCL snippet to configure the kubernetes/helm provider pointing at this cluster."
  sensitive   = true
  value       = <<-EOT
    provider "kubernetes" {
      host                   = "https://${module.gke.endpoint}"
      token                  = data.google_client_config.default.access_token
      cluster_ca_certificate = base64decode("${module.gke.ca_certificate}")
    }
  EOT
}
