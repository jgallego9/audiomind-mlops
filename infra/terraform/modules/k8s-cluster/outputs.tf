output "cluster_name" {
  description = "Validated cluster name."
  value       = var.cluster_name
}

output "node_count" {
  description = "Desired number of CPU worker nodes."
  value       = var.node_count
}

output "gpu_node_count" {
  description = "Desired number of GPU worker nodes (0 = GPU node group disabled)."
  value       = var.gpu_node_count
}

output "gpu_instance_type" {
  description = "Instance / machine type for GPU nodes."
  value       = var.gpu_instance_type
}

output "kubernetes_version" {
  description = "Kubernetes version string as passed to this module."
  value       = var.kubernetes_version
}
