# Stage 1: Install dependencies
FROM docker.io/library/node:22-alpine AS deps

RUN apk add --no-cache libc6-compat

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN npm install -g pnpm@latest

WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --prefer-offline --ignore-scripts

# Stage 2: Build Next.js app
FROM docker.io/library/node:22-alpine AS builder

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN npm install -g pnpm@latest

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* vars are baked into the client bundle at build time.
# NEXT_PUBLIC_API_URL must be absolute because settings.mjs does new URL(NEXT_PUBLIC_API_URL).
# For local dev on port 7087; set via build-arg to override for other envs.
ARG NEXT_PUBLIC_API_URL=http://localhost:7087/api/dalia/v1
ARG NEXT_PUBLIC_BASE_PATH=
ARG NEXT_PUBLIC_SPARQL_MAX_LIMIT=1000

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_BASE_PATH=${NEXT_PUBLIC_BASE_PATH}
ENV NEXT_PUBLIC_SPARQL_MAX_LIMIT=${NEXT_PUBLIC_SPARQL_MAX_LIMIT}
ENV NEXT_TELEMETRY_DISABLED=1

RUN pnpm run build

# Stage 3: Production runner
FROM docker.io/library/node:22-alpine AS runner

RUN apk add --no-cache curl

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy standalone output (minimal bundle: server.js + minimal node_modules)
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
# Copy static assets next to standalone server (required for Next.js standalone to serve them)
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
# Copy public directory
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# server.js is created by Next.js build from standalone output
CMD ["node", "server.js"]
