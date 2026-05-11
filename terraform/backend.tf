terraform {
  backend "s3" {
    bucket         = "ecommerce-tfstate-528757804354"
    key            = "ecommerce/dev/terraform.tfstate"
    region         = "ap-south-1"
    encrypt        = true
  }
}