ARG APP_SITE

# base stage
FROM public.ecr.aws/lambda/python:3.8 as base

ENV \
    # write-out stdout/stderr immediately
    PYTHONUNBUFFERED=1 \
    # prevents python creating .pyc files
    PYTHONDONTWRITEBYTECODE=1 \
    \
    # poetry
    POETRY_HOME=/opt/poetry \
    \
    APP_SITE_PACKAGES=/var/lang/lib/python3.8/site-packages \
    APP_DIR=${LAMBDA_TASK_ROOT}

ENV PATH="$POETRY_HOME/bin:$PATH"

# builder stage
FROM base AS builder

RUN \
    pip install poetry && \
    poetry --version && \
    (test -d || mkdir ${APP_DIR})

COPY pyproject.toml poetry.lock ${APP_DIR}
RUN \
    cd ${APP_DIR} && \
    poetry export \
        --no-interaction --no-ansi -vvv \
        -f requirements.txt --without-hashes \
        | pip3 install -r /dev/stdin

# runtime image
FROM base AS runtime

COPY --from=builder ${APP_SITE_PACKAGES} ${APP_SITE_PACKAGES}
COPY . ${APP_DIR}

# You can overwrite command in `serverless.yml` template
CMD ["app.handler"]
