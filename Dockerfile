# mecab-ipadic-neologd builder stage
ARG APP_NEOLOGD_DIR=/opt/mecab-ipadic-neologd

FROM debian:bullseye-slim as neologd-builder

ARG APP_SRC_DIR=/usr/local/src/mecab-ipadic-neologd
ARG APP_NEOLOGD_DIR

RUN apt-get update
RUN apt-get install \
    --no-install-recommends \
    -y \
    mecab libmecab-dev mecab-ipadic-utf8 git make curl xz-utils file \
    ca-certificates patch

RUN git clone --depth=1 https://github.com/neologd/mecab-ipadic-neologd.git /usr/local/src/mecab-ipadic-neologd
RUN mkdir -p ${APP_NEOLOGD_DIR}
RUN ${APP_SRC_DIR}/bin/install-mecab-ipadic-neologd \
    --newest \
    --forceyes \
    --asuser \
    --prefix ${APP_NEOLOGD_DIR}

# base stage
FROM public.ecr.aws/lambda/python:3.8 as base

ARG APP_NEOLOGD_DIR
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
    APP_DIR=${LAMBDA_TASK_ROOT} \
    APP_NEOLOGD_DIR=${APP_NEOLOGD_DIR}

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
COPY --from=neologd-builder ${APP_NEOLOGD_DIR} ${APP_NEOLOGD_DIR}

# You can overwrite command in `serverless.yml` template
CMD ["app.handler"]
