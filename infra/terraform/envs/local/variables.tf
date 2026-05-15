variable "cluster_name" {
  description = "Name of the kind cluster."
  type        = string
  default     = "audiomind"
}

variable "kubernetes_version" {
  description = "Kubernetes version for the kind node image (e.g. 1.32.0)."
  type        = string
  default     = "1.32.0"
}

variable "node_count" {
  description = "Number of worker nodes (control-plane node is always created separately)."
  type        = number
  default     = 2
}

variable "metallb_address_pool" {
  description = "IP range for the MetalLB IPAddressPool. Must fall inside the Docker kind bridge network (default: 172.18.0.200-172.18.0.250)."
  type        = string
  default     = "172.18.0.200-172.18.0.250"
}

variable "metallb_chart_version" {
  description = "Helm chart version for MetalLB."
  type        = string
  default     = "0.14.9"
}
