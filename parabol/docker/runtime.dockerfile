# syntax=docker/dockerfile:1

FROM parabol:base
WORKDIR /home/node/parabol

COPY --from=parabol:builder /app/dist ./dist
COPY --from=parabol:builder /app/build ./build
COPY --from=parabol:builder /app/node_modules ./node_modules
COPY --from=parabol:builder /app/pnpm-lock.yaml ./pnpm-lock.yaml

USER node
