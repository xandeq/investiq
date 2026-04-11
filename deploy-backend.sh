#!/usr/bin/env bash
# deploy-backend.sh — InvestIQ Backend Deploy Script
# Copies Python app to container without rebuilding Docker image
# Usage: bash deploy-backend.sh [--migrate]
#   --migrate  Run alembic upgrade head after deploy

set -euo pipefail

PLINK="/c/Program Files/PuTTY/plink"
VPS_HOST="185.173.110.180"
VPS_USER="root"
VPS_PASSWORD="E)0a?FdCBjwJk@ARRqRE"
CONTAINER="financas-backend-1"
PROJECT_DIR="/d/claude-code/investiq"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

RUN_MIGRATE=false
for arg in "$@"; do
  [[ "$arg" == "--migrate" ]] && RUN_MIGRATE=true
done

vps() {
  "$PLINK" -batch -pw "$VPS_PASSWORD" "${VPS_USER}@${VPS_HOST}" "$@"
}

echo ""
echo "=================================================="
echo "  InvestIQ Backend Deploy"
echo "=================================================="
echo ""

# ── Upload app/ directory ──────────────────────────────
info "Step 1/3: Uploading backend/app to VPS..."
cd "$PROJECT_DIR/backend"

(tar czf - app/) | \
  "$PLINK" -batch -pw "$VPS_PASSWORD" "${VPS_USER}@${VPS_HOST}" \
  "mkdir -p /tmp/be-deploy && tar xzf - -C /tmp/be-deploy"

success "Upload complete."

# ── Copy into container ────────────────────────────────
info "Step 2/3: Applying to container..."
vps "
set -e
# Create tar of app dir and docker cp it
cd /tmp/be-deploy && tar czf /tmp/backend-app.tar.gz app/
docker cp /tmp/backend-app.tar.gz ${CONTAINER}:/tmp/
docker exec ${CONTAINER} sh -c 'cd /app && tar -xzf /tmp/backend-app.tar.gz'
echo 'Backend files copied.'
"
success "Container updated."

# ── Migrate ────────────────────────────────────────────
if [[ "$RUN_MIGRATE" == "true" ]]; then
  info "Step 3/3: Running migrations..."
  vps "docker exec ${CONTAINER} alembic upgrade head"
  success "Migrations applied."
else
  info "Step 3/3: Skipping migrations (pass --migrate to run)"
fi

# ── Restart ────────────────────────────────────────────
info "Restarting backend container..."
vps "docker restart ${CONTAINER}"
sleep 4

HTTP_STATUS=$(vps "curl -s -o /dev/null -w '%{http_code}' http://localhost:8100/health 2>/dev/null || echo 000")
if [[ "$HTTP_STATUS" == "200" ]]; then
  success "Backend is UP (HTTP $HTTP_STATUS)"
else
  warn "Backend returned HTTP $HTTP_STATUS — check logs:"
  vps "docker logs ${CONTAINER} --tail 20" || true
fi

vps "rm -rf /tmp/be-deploy /tmp/backend-app.tar.gz"

echo ""
echo "=================================================="
success "Backend deploy complete!"
echo "=================================================="
echo ""
