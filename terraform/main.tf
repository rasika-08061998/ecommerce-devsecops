# ─── VPC Module ───────────────────────────────────────────────
module "vpc" {
  source = "./modules/vpc"

  project            = var.project
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
}

# ─── ECR Module ───────────────────────────────────────────────
module "ecr" {
  source = "./modules/ecr"

  project     = var.project
  environment = var.environment
  services = [
    "api-gateway",
    "user-service",
    "product-service",
    "order-service",
    "payment-service",
    "frontend"
  ]
}

# ─── EKS Module ───────────────────────────────────────────────
module "eks" {
  source = "./modules/eks"

  project                = var.project
  environment            = var.environment
  vpc_id                 = module.vpc.vpc_id
  private_subnet_ids     = module.vpc.private_subnet_ids
  eks_cluster_version    = var.eks_cluster_version
  eks_node_instance_type = var.eks_node_instance_type
  eks_node_desired       = var.eks_node_desired
  eks_node_min           = var.eks_node_min
  eks_node_max           = var.eks_node_max

  depends_on = [module.vpc]
}

# ─── IAM Module ───────────────────────────────────────────────
module "iam" {
  source = "./modules/iam"

  project            = var.project
  environment        = var.environment
  aws_account_id     = var.aws_account_id
  github_repo        = var.github_repo
  oidc_issuer        = module.eks.oidc_issuer
  ecr_repository_arns = module.ecr.repository_arns

  depends_on = [module.eks]
}