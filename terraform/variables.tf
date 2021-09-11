# An evironment name, to be used in resource names
# e.g. dev, prd
variable "env" {
  type    = string
  default = "dev"
}

# The project name, to be used in resource names
variable "service" {
  type    = string
  default = "mecab-function"
}

variable "userdic" {
  type = string
}
