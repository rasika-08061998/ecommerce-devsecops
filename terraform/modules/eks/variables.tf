variable "project" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where EKS cluster will be created"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for EKS nodes"
  type        = list(string)
}

variable "eks_cluster_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
}

variable "eks_node_instance_type" {
  description = "EC2 instance type for worker nodes"
  type        = string
}

variable "eks_node_desired" {
  description = "Desired number of worker nodes"
  type        = number
}

variable "eks_node_min" {
  description = "Minimum number of worker nodes"
  type        = number
}

variable "eks_node_max" {
  description = "Maximum number of worker nodes"
  type        = number
}