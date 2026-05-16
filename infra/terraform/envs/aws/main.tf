module "cluster_config" {
  source = "../../modules/k8s-cluster"

  cluster_name       = var.cluster_name
  node_count         = var.node_count
  gpu_node_count     = var.gpu_node_count
  gpu_instance_type  = var.gpu_instance_type
  kubernetes_version = var.kubernetes_version
}

locals {
  # Use the first 3 available AZs in the selected region.
  azs = slice(data.aws_availability_zones.available.names, 0, 3)

  # Derive private and public subnets from the VPC CIDR.
  private_subnets = [for i in range(3) : cidrsubnet(var.vpc_cidr, 4, i)]
  public_subnets  = [for i in range(3) : cidrsubnet(var.vpc_cidr, 8, 100 + i)]

  tags = merge(
    {
      Terraform   = "true"
      Environment = "dev"
      Project     = "moiraweave"
    },
    var.tags,
  )

  # GPU node group definition; conditionally merged into eks_managed_node_groups.
  gpu_node_group = var.gpu_node_count > 0 ? {
    gpu = {
      ami_type       = "AL2023_x86_64_NVIDIA"
      instance_types = [module.cluster_config.gpu_instance_type]
      min_size       = 0
      max_size       = module.cluster_config.gpu_node_count + 1
      desired_size   = module.cluster_config.gpu_node_count

      taints = {
        gpu = {
          key    = "nvidia.com/gpu"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      }

      labels = {
        "nvidia.com/gpu" = "true"
      }
    }
  } : {}
}

# ─── VPC ─────────────────────────────────────────────────────────────────────
# ref: https://registry.terraform.io/modules/terraform-aws-modules/vpc/aws/6.6.1

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 6.6"

  name = "${module.cluster_config.cluster_name}-vpc"
  cidr = var.vpc_cidr

  azs             = local.azs
  private_subnets = local.private_subnets
  public_subnets  = local.public_subnets

  enable_nat_gateway   = true
  single_nat_gateway   = true  # single NAT GW is sufficient for dev/staging
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Subnet tags required for EKS ALB / NLB controller discovery.
  public_subnet_tags = {
    "kubernetes.io/role/elb"                                        = "1"
    "kubernetes.io/cluster/${module.cluster_config.cluster_name}"   = "owned"
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"                               = "1"
    "kubernetes.io/cluster/${module.cluster_config.cluster_name}"   = "owned"
  }

  tags = local.tags
}

# ─── EKS ─────────────────────────────────────────────────────────────────────
# ref: https://registry.terraform.io/modules/terraform-aws-modules/eks/aws/21.20.0

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"

  name               = module.cluster_config.cluster_name
  kubernetes_version = module.cluster_config.kubernetes_version

  endpoint_public_access = true

  # Add the Terraform caller IAM identity as a cluster admin via access entry.
  enable_cluster_creator_admin_permissions = true

  # IRSA: create an OIDC provider so pods can assume IAM roles via service accounts.
  enable_irsa = true

  authentication_mode = "API_AND_CONFIG_MAP"

  addons = {
    coredns = {}
    eks-pod-identity-agent = {
      # Install before worker nodes join so IRSA / Pod Identity is ready immediately.
      before_compute = true
    }
    kube-proxy = {}
    vpc-cni = {
      before_compute = true
    }
  }

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = merge(
    {
      cpu = {
        ami_type       = "AL2023_x86_64_STANDARD"
        instance_types = ["t3.xlarge"]
        min_size       = 1
        max_size       = module.cluster_config.node_count + 2
        desired_size   = module.cluster_config.node_count
      }
    },
    local.gpu_node_group,
  )

  tags = local.tags
}

# ─── ECR repositories ─────────────────────────────────────────────────────────

resource "aws_ecr_repository" "moiraweave" {
  for_each = toset(["api", "worker", "drift-detector"])

  name                 = "moiraweave/${each.key}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.tags
}

resource "aws_ecr_lifecycle_policy" "moiraweave" {
  for_each   = aws_ecr_repository.moiraweave
  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Retain last 10 images per repository"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
