# ─────────────────────────────────────────────────────────────────────────────
# Cloud-agnostic k8s-cluster module — interface definition
#
# This module defines the shared variable interface that every cloud-specific
# environment (local / AWS / GCP) must honour.  It contains no cloud resources;
# each environment root module calls this module to centralise input validation
# and then creates cloud-specific resources using the validated outputs.
# ─────────────────────────────────────────────────────────────────────────────

variable "cluster_name" {
  description = "Logical name of the Kubernetes cluster (used as a name prefix for all resources)."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,38}[a-z0-9]$", var.cluster_name))
    error_message = "cluster_name must be 3–40 lowercase alphanumeric characters or hyphens, starting and ending with a letter or digit."
  }
}

variable "node_count" {
  description = "Desired number of general-purpose (CPU) worker nodes."
  type        = number
  default     = 2

  validation {
    condition     = var.node_count >= 1
    error_message = "node_count must be at least 1."
  }
}

variable "gpu_node_count" {
  description = "Desired number of GPU worker nodes. Set to 0 to disable the GPU node group entirely."
  type        = number
  default     = 0

  validation {
    condition     = var.gpu_node_count >= 0
    error_message = "gpu_node_count must be >= 0."
  }
}

variable "gpu_instance_type" {
  description = "Cloud-specific instance / machine type for GPU nodes (e.g. g4dn.xlarge on AWS, n1-standard-4 on GCP). Ignored when gpu_node_count = 0."
  type        = string
  default     = ""
}

variable "kubernetes_version" {
  description = "Kubernetes control-plane version. Accepts cloud-provider formats (e.g. '1.33' on EKS, 'latest' on GKE, '1.32.0' for kind)."
  type        = string
  default     = "latest"
}
