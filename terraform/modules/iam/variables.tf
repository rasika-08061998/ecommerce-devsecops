variable "project" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository in format owner/repo-name"
  type        = string
}

variable "oidc_issuer" {
  description = "OIDC issuer URL from EKS cluster"
  type        = string
}

variable "ecr_repository_arns" {
  description = "Map of ECR repository ARNs"
  type        = map(string)
}