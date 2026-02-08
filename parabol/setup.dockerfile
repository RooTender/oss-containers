# syntax=docker/dockerfile:1

######## BUILDER ########
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

COPY pnpm-lock.yaml package.json pnpm-workspace.yaml ./
COPY packages ./packages

RUN --mount=type=cache,id=pnpm-store,target=/root/.local/share/pnpm/store \
    corepack enable pnpm \
 && pnpm install --frozen-lockfile

COPY . .
RUN pnpm build \
 && pnpm prune --prod

######## RUNTIME ########
FROM node:22-alpine AS runtime
WORKDIR /home/node/parabol

ENV NODE_ENV=production

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/build ./build
COPY --from=builder /app/node_modules ./node_modules

USER node
CMD ["node", "dist/web.js"]
