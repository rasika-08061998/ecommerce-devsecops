output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions IAM role"
  value       = aws_iam_role.github_actions.arn
}

output "github_actions_role_name" {
  description = "Name of the GitHub Actions IAM role"
  value       = aws_iam_role.github_actions.name
}

output "github_oidc_provider_arn" {
  description = "ARN of the GitHub OIDC provider"
  value       = aws_iam_openid_connect_provider.github.arn
}

output "ecr_push_policy_arn" {
  description = "ARN of the ECR push policy"
  value       = aws_iam_policy.ecr_push.arn
}

output "eks_deploy_policy_arn" {
  description = "ARN of the EKS deploy policy"
  value       = aws_iam_policy.eks_deploy.arn
}