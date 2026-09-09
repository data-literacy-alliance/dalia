# Migration from npm to pnpm - Speed Up Your Builds!

## Why pnpm?

Based on 2025 benchmarks, pnpm is **significantly faster** than npm:

| Scenario | npm | pnpm | **Improvement** |
|----------|-----|------|-----------------|
| Clean install | 28.6s | 9.5s | **3x faster** |
| With cache | 1.3s | 749ms | **2x faster** |
| CI/CD (20 builds/day) | - | - | **Save 104 min/day** |

**Additional benefits:**
- ✅ Used by Next.js, Vue, Material UI
- ✅ Content-addressable storage (saves disk space)
- ✅ Hard links instead of duplicates
- ✅ Faster in Docker environments

## Quick Migration (3 Steps)

### Step 1: Run Migration Script

```bash
cd /home/mzubilewicz/daliaproject/prod/frontend
./migrate-to-pnpm.sh
```

This script will:
1. Install pnpm globally
2. Backup your package-lock.json
3. Generate pnpm-lock.yaml
4. Install dependencies

### Step 2: Update Your Build Script

Replace your current Dockerfile with the optimized pnpm version:

```bash
# Backup current Dockerfile
cp Dockerfile Dockerfile.npm.backup

# Use the new pnpm Dockerfile
cp Dockerfile.pnpm Dockerfile
```

### Step 3: Update .dockerignore (if needed)

Add to `.dockerignore` if not already present:
```
node_modules
.pnpm-store
.next
```

## Expected Results

### Before (npm)
```
[2/4] STEP 6/6: RUN npm ci ...
⏱️  Duration: ~10 minutes
```

### After (pnpm)
```
[2/4] STEP 6/6: RUN pnpm install ...
⏱️  Duration: ~5-10 seconds (first build)
⏱️  Duration: ~1-2 seconds (cached builds)
```

## Build Command Updates

No changes needed for Docker build commands. Just rebuild:

```bash
# Your existing build command will work
docker build -t your-image:tag .
```

## Verification

After migration, verify everything works:

```bash
# Development
pnpm dev

# Build
pnpm build

# Start production
pnpm start
```

## Rollback (if needed)

If you need to rollback to npm:

```bash
# Restore original Dockerfile
cp Dockerfile.npm.backup Dockerfile

# Remove pnpm files
rm -rf node_modules pnpm-lock.yaml

# Restore package-lock.json
cp package-lock.json.backup package-lock.json

# Reinstall with npm
npm ci
```

## Key Differences

| Command | npm | pnpm |
|---------|-----|------|
| Install | `npm install` | `pnpm install` |
| Install (CI) | `npm ci` | `pnpm install --frozen-lockfile` |
| Add package | `npm install pkg` | `pnpm add pkg` |
| Remove package | `npm uninstall pkg` | `pnpm remove pkg` |
| Run script | `npm run dev` | `pnpm dev` |
| Update all | `npm update` | `pnpm update` |

## Dockerfile Optimizations Included

The new `Dockerfile.pnpm` includes:

1. **pnpm cache mount**: Reuses downloaded packages across builds
2. **Standalone output**: Minimal production bundle (already enabled in next.config.mjs)
3. **Multi-stage build**: Separates deps, build, and runtime
4. **Layer optimization**: Better caching for faster rebuilds
5. **--frozen-lockfile**: Ensures deterministic builds

## Troubleshooting

### "pnpm: command not found"
```bash
npm install -g pnpm
```

### Build still slow?
- Ensure Docker BuildKit is enabled: `export DOCKER_BUILDKIT=1`
- Check cache is working: Look for `CACHED` in build output
- Verify pnpm-lock.yaml exists and is committed

### Packages missing?
```bash
pnpm install --frozen-lockfile
```

## Sources

- [pnpm vs npm Speed Comparison](https://mindlore.blog/pnpm/)
- [pnpm-next-docker](https://github.com/mpash/pnpm-next-docker)
- [Dockerizing Next.js with pnpm](https://medium.com/@she11fish/dockerizing-next-js-15-application-with-pnpm-for-production-39c841ce8323)
- [pnpm Performance Benchmarks](https://javascript-conference.com/blog/pnpm-the-high-performance-package-manager/)
