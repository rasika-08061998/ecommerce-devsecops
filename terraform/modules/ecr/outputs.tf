output "repository_urls" {
  description = "Map of service name to ECR repository URL"
  value = {
    for service, repo in aws_ecr_repository.services :
    service => repo.repository_url
  }
}

output "repository_arns" {
  description = "Map of service name to ECR repository ARN"
  value = {
    for service, repo in aws_ecr_repository.services :
    service => repo.arn
  }
}

output "registry_id" {
  description = "ECR registry ID (AWS Account ID)"
  value       = values(aws_ecr_repository.services)[0].registry_id
}