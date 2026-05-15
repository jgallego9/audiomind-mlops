output "cluster_name" {
  description = "EKS cluster name."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS API server endpoint."
  value       = module.eks.cluster_endpoint
}

output "cluster_ca_certificate" {
  description = "Base64 encoded CA certificate for the EKS cluster."
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "oidc_provider_arn" {
  description = "ARN of the OIDC provider created for IRSA."
  value       = module.eks.oidc_provider_arn
}

output "vpc_id" {
  description = "ID of the VPC created for the EKS cluster."
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets used by EKS worker nodes."
  value       = module.vpc.private_subnets
}

output "ecr_repository_urls" {
  description = "ECR repository URLs keyed by service name (api, worker, drift-detector)."
  value       = { for k, v in aws_ecr_repository.inferflow : k => v.repository_url }
}
