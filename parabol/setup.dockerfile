FROM parabol:base as builder

USER root
WORKDIR /build

RUN apt-get update && apt-get install -y \
    build-essential \
    python3 \
    libvips

COPY pnpm-workspace.yaml ./
COPY package.json pnpm-lock.yaml ./
COPY packages ./packages

RUN corepack enable && \
    pnpm install --prod --shamefully-hoist --ignore-scripts && \
    pnpm store prune

# ---- runtime image ----

FROM parabol:base

WORKDIR /home/node/parabol

COPY --from=builder /build/node_modules ./node_modules

USER node
