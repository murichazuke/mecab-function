# mecab-ipadic-neologd builder stage
# ==================================

ARG APP_NEOLOGD_DIR=/opt/mecab-ipadic-neologd

FROM debian:bullseye-slim as neologd-builder

ARG APP_SRC_DIR=/usr/local/src/mecab-ipadic-neologd
ARG APP_NEOLOGD_DIR
ENV LC_ALL=C.UTF-8

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

# Base stage
# ==========

FROM public.ecr.aws/lambda/python:3.8 as base

ARG APP_NEOLOGD_DIR
ENV \
    # write-out stdout/stderr immediately
    PYTHONUNBUFFERED=1 \
    # prevents python from creating annoying .pyc files
    PYTHONDONTWRITEBYTECODE=1 \
    \
    # pip
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    \
    # Poetry installation location
    POETRY_HOME=/opt/poetry \
    # Let poetry install packages system-widely
    POETRY_VIRTUALENVS_CREATE=false \
    \
    # application specific variables
    APP_SITE_PACKAGES=/var/lang/lib/python3.8/site-packages \
    APP_DIR=${LAMBDA_TASK_ROOT} \
    APP_NEOLOGD_DIR=${APP_NEOLOGD_DIR}

ENV PATH="${POETRY_HOME}/bin:${PATH}"

# Builder stage
# =============

FROM base AS builder

RUN \
    curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py \
        | /var/lang/bin/python -

RUN \
    # Required to build neologdn
    yum install -y gcc-c++

COPY pyproject.toml poetry.lock ${APP_DIR}/
RUN \
    cd ${APP_DIR} && \
    poetry install --no-dev --no-interaction --no-ansi -vvv

# Runtime image
# =============

FROM base AS runtime

COPY --from=public.ecr.aws/sentry/sentry-python-serverless-sdk:6 /opt/ /opt
COPY --from=builder ${APP_SITE_PACKAGES} ${APP_SITE_PACKAGES}
COPY . ${APP_DIR}
COPY --from=neologd-builder ${APP_NEOLOGD_DIR} ${APP_NEOLOGD_DIR}

# You can overwrite command in `serverless.yml` template
CMD ["sentry_sdk.integrations.init_serverless_sdk.sentry_lambda_handler"]

# Develop image
# =============

FROM runtime AS dev

COPY --from=builder ${POETRY_HOME} ${POETRY_HOME}

RUN \
    cd ${APP_DIR} && \
    poetry install --no-interaction --no-ansi -vvv

WORKDIR ${APP_DIR}
ENTRYPOINT []
CMD ["python", "-c", "import signal as s; s.sigwait([s.SIGINT])"]
