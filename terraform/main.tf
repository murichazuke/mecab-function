# The global configuration

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "3.40.0"
    }
  }
  required_version = ">= 0.13"
}

provider "aws" {
  profile = "default"
  region  = "ap-northeast-1"
}

locals {
  # env-service-resource_name-type_suffix
  # @see https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/other-aws-resource-types.html
  name_format = "${var.env}-${var.service}-%s-%s"
  common_tags = {
    Environment = var.env
    Service     = var.service
  }
}

resource "aws_iam_user" "circleci" {
  name = format(local.name_format, "circleci", "user")
}

resource "aws_iam_user_policy" "circleci" {
  count = 0
  name = format(local.name_format, "circleci", "policy")
  user = aws_iam_user.circleci.name

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
      }
    ]
  })
}

resource "aws_iam_access_key" "circleci" {
  user = aws_iam_user.circleci.name
}

resource "aws_s3_bucket" "userdic" {
  bucket = format(local.name_format, "userdic", "bucket")
}

resource "aws_s3_bucket_object" "userdic" {
  key    = "path/to/user.dic"
  bucket = aws_s3_bucket.userdic.id
  source = var.userdic
  acl    = "private"
}
