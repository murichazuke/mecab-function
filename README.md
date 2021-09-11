# Serverless - AWS Python Docker

This project has been generated using the `aws-nodejs-docker` template from the [Serverless framework](https://www.serverless.com/).

For detailed instructions, please refer to the [documentation](https://www.serverless.com/framework/docs/providers/aws/).

## Deployment instructions

> **Requirements**: Docker. In order to build images locally and push them to ECR, you need to have Docker installed on your local machine. Please refer to [official documentation](https://docs.docker.com/get-docker/).

In order to deploy your service, run the following command

```
sls deploy
```

## Run your service

After successful deployment, you can test your service remotely by using the following command:

```
sls invoke --function hello
```

## Run the function locally

```bash
$ docker-compose exec workspace python app.py --output=json --data='{"body": "中居正広のこおりつけ"}'
```

## Run linters and unittests

```bash
$ docker-compose exec workspace poetry run tox
```
