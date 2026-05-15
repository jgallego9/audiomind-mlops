variable "project_id" {
  description = "GCP project ID that will host the GKE cluster and Artifact Registry."
  type        = string
}

variable "region" {
  description = "GCP region for all resources."
  type        = string
  default     = "us-central1"
}

variable "zones" {
  description = "List of GCP zones for the GKE node pools (regional cluster uses all listed zones)."
  type        = list(string)
  default     = ["us-central1-a", "us-central1-b", "us-central1-f"]
}

variable "cluster_name" {
  description = "Name of the GKE cluster (also used as a network/resource prefix)."
  type        = string
  default     = "audiomind"
}

variable "kubernetes_version" {
  description = "Kubernetes version for the GKE masters. Use 'latest' to always provision the latest available version in the selected release channel."
  type        = string
  default     = "latest"
}

variable "node_count" {
  description = "Initial number of CPU worker nodes per zone."
  type        = number
  default     = 1
}

variable "gpu_node_count" {
  description = "Maximum number of GPU nodes in the GPU node pool. Set to 0 to disable the pool."
  type        = number
  default     = 0
}

variable "gpu_accelerator_type" {
  description = "GCE accelerator type for GPU nodes (e.g. nvidia-tesla-t4)."
  type        = string
  default     = "nvidia-tesla-t4"
}

variable "deletion_protection" {
  description = "When true, Terraform cannot destroy the GKE cluster. Set to false only for non-production environments."
  type        = bool
  default     = true
}
