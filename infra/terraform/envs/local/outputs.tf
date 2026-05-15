output "cluster_name" {
  description = "Name of the kind cluster."
  value       = kind_cluster.this.name
}

output "cluster_endpoint" {
  description = "Kubernetes API server endpoint."
  value       = kind_cluster.this.endpoint
}

output "cluster_ca_certificate" {
  description = "CA certificate (base64 encoded) of the kind cluster."
  value       = kind_cluster.this.cluster_ca_certificate
  sensitive   = true
}

output "kubeconfig" {
  description = "kubeconfig content for the kind cluster."
  value       = kind_cluster.this.kubeconfig
  sensitive   = true
}
