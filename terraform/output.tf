
output "aws_iam_circleci_access_key_id" {
  value = aws_iam_access_key.circleci.id
}

output "aws_iam_circleci_secret_access_key" {
  sensitive = true
  value     = aws_iam_access_key.circleci.secret
}
