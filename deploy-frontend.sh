#!/usr/bin/env bash
# deploy-frontend.sh — InvestIQ Frontend Deploy Script
# Builds locally and deploys to VPS via plink/pscp
# Usage: bash deploy-frontend.sh [--skip-build]
#
# What it does:
# 1. Build Next.js (standalone) locally
# 2. Copy static files into standalone
# 3. Upload to VPS (tar pipe via plink)
# 4. Apply proxy patch (localhost:8100 → http://backend:8000)
# 5. Restart container

set -euo pipefail

PLINK="/c/Program Files/PuTTY/plink"
# Load only VPS secrets from ~/.claude/.secrets.env (safe parsing)
if [[ -f "$HOME/.claude/.secrets.env" ]]; then
  VPS_HOST=$(grep "^VPS_HOST=" "$HOME/.claude/.secrets.env" | cut -d'=' -f2)
  VPS_USER=$(grep "^VPS_USER=" "$HOME/.claude/.secrets.env" | cut -d'=' -f2)
  VPS_PASSWORD=$(grep "^VPS_PASSWORD=" "$HOME/.claude/.secrets.env" | cut -d'=' -f2)
else
  echo "ERROR: ~/.claude/.secrets.env not found" >&2
  exit 1
fi
CONTAINER="financas-frontend-1"
FRONTEND_DIR="/d/claude-code/investiq/frontend"

# Colours
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

SKIP_BUILD=false
for arg in "$@"; do
  [[ "$arg" == "--skip-build" ]] && SKIP_BUILD=true
done

# Helper: run command on VPS
vps() {
  "$PLINK" -batch -pw "$VPS_PASSWORD" "${VPS_USER}@${VPS_HOST}" "$@"
}

echo ""
echo "=================================================="
echo "  InvestIQ Frontend Deploy"
echo "=================================================="
echo ""

# ── STEP 1: Build ──────────────────────────────────────
if [[ "$SKIP_BUILD" == "false" ]]; then
  info "Step 1/5: Building Next.js (standalone)..."
  cd "$FRONTEND_DIR"
  npm run build
  success "Build complete."
else
  info "Step 1/5: Skipping build (--skip-build)"
  cd "$FRONTEND_DIR"
fi

# ── STEP 2: Prepare standalone ─────────────────────────
info "Step 2/5: Preparing standalone directory..."

# Copy static assets into standalone
if [[ -d ".next/static" ]]; then
  cp -r .next/static .next/standalone/.next/static
  success "Copied .next/static → standalone"
fi

# Copy public folder if it exists
if [[ -d "public" ]]; then
  cp -r public .next/standalone/public
  success "Copied public → standalone"
fi

# ── STEP 3: Upload to VPS ──────────────────────────────
info "Step 3/5: Uploading to VPS..."

# Clean remote temp dir
vps "rm -rf /tmp/fe-deploy && mkdir -p /tmp/fe-deploy/standalone"

# Upload standalone WITHOUT node_modules — container keeps Alpine-compiled binaries (sharp, @swc)
# Container CMD is: node .next/standalone/server.js — files must be at /app/.next/standalone/
info "  Uploading .next/standalone (excluding node_modules — keeps Alpine Linux binaries)..."
(cd .next/standalone && tar czf - --exclude='./node_modules' .) | \
  "$PLINK" -batch -pw "$VPS_PASSWORD" "${VPS_USER}@${VPS_HOST}" \
  "tar xzf - -C /tmp/fe-deploy/standalone"

success "Upload complete."

# ── STEP 4: Apply to container ─────────────────────────
info "Step 4/5: Applying to container..."

vps "
set -e

# Tar the standalone (no node_modules) and docker cp into the correct container path
cd /tmp/fe-deploy/standalone && tar czf /tmp/fe-deploy/standalone.tar.gz .
docker cp /tmp/fe-deploy/standalone.tar.gz ${CONTAINER}:/tmp/

# Wipe only app code files inside standalone — PRESERVE node_modules (Alpine Linux binaries)
# node_modules from a Windows build would be wrong architecture (musl vs glibc/PE)
docker exec ${CONTAINER} sh -c '
  find /app/.next/standalone -mindepth 1 -maxdepth 1 ! -name node_modules -exec rm -rf {} +
  tar xzf /tmp/standalone.tar.gz -C /app/.next/standalone
'

echo 'Files copied to container (node_modules preserved).'

# Apply proxy patch — replace any localhost:8100 refs with internal docker service name
docker exec ${CONTAINER} sh -c '
  find /app/.next -name \"*.json\" -o -name \"server.js\" | xargs -I{} \
    sed -i \"s|http://localhost:8100|http://backend:8000|g\" {} 2>/dev/null
  echo \"Proxy patch applied.\"
'
"
success "Container updated."

# ── STEP 5: Restart & verify ───────────────────────────
info "Step 5/5: Restarting container..."
vps "docker restart ${CONTAINER}"

# Wait for container to come up
info "  Waiting for container to start..."
sleep 5

# Health check
HTTP_STATUS=$(vps "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000 2>/dev/null || echo 000")
if [[ "$HTTP_STATUS" == "200" || "$HTTP_STATUS" == "307" || "$HTTP_STATUS" == "302" || "$HTTP_STATUS" == "301" ]]; then
  success "Container is UP (HTTP $HTTP_STATUS)"
else
  warn "Container returned HTTP $HTTP_STATUS — check logs:"
  vps "docker logs ${CONTAINER} --tail 20" || true
fi

# Cleanup temp files on VPS
vps "rm -rf /tmp/fe-deploy"

echo ""
echo "=================================================="
success "Deploy complete! https://investiq.com.br"
echo "=================================================="
echo ""
