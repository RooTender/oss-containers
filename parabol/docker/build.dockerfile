# syntax=docker/dockerfile:1

FROM node:22-trixie-slim AS builder
WORKDIR /app

ARG PUBLIC_URL
ARG CDN_BASE_URL
ARG DD_GIT_COMMIT_SHA
ARG DD_GIT_REPOSITORY_URL

ENV PUBLIC_URL=${PUBLIC_URL}
ENV CDN_BASE_URL=${CDN_BASE_URL}
ENV DD_GIT_COMMIT_SHA=${DD_GIT_COMMIT_SHA}
ENV DD_GIT_REPOSITORY_URL=${DD_GIT_REPOSITORY_URL}
ENV CI=true

RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN node patch.js

RUN --mount=type=cache,id=pnpm-store,target=/root/.local/share/pnpm/store \
    corepack enable pnpm && pnpm install --frozen-lockfile --ignore-scripts
RUN pnpm build
RUN pnpm prune --prod
