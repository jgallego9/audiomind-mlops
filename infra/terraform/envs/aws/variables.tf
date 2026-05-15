variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Name of the EKS cluster (also used as a resource prefix)."
  type        = string
  default     = "inferflow"
}

variable "kubernetes_version" {
  description = "Kubernetes version for the EKS control plane (e.g. '1.33')."
  type        = string
  default     = "1.33"
}

variable "node_count" {
  description = "Desired number of general-purpose CPU worker nodes."
  type        = number
  default     = 2
}

variable "gpu_node_count" {
  description = "Desired number of GPU worker nodes. Set to 0 to disable the GPU managed node group."
  type        = number
  default     = 0
}

variable "gpu_instance_type" {
  description = "EC2 instance type for GPU nodes."
  type        = string
  default     = "g4dn.xlarge"
}

variable "vpc_cidr" {
  description = "CIDR block for the dedicated VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "tags" {
  description = "Additional tags applied to all resources."
  type        = map(string)
  default     = {}
}
