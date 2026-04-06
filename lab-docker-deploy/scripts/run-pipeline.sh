#!/bin/bash
#
# =============================================================================
#  DOCKER & DEPLOYMENT PIPELINE SIMULATOR
# =============================================================================
#
#  This script simulates what happens in Labs 7 & 8:
#  building a Docker image, running the container, and testing it.
#
#  The Pipeline Stages:
#
#   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
#   │ 1.CHECK  │─>│ 2.DEPS   │─>│ 3.UNIT   │─>│ 4.DOCKER │
#   │  files   │  │ install  │  │  tests   │  │  check   │
#   └──────────┘  └──────────┘  └──────────┘  └──────────┘
#        │
#        v
#   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
#   │ 5.BUILD  │─>│ 6.RUN    │─>│ 7.HEALTH │─>│ 8.CLEAN  │
#   │  image   │  │container │  │  check   │  │   up     │
#   └──────────┘  └──────────┘  └──────────┘  └──────────┘
#
#  Usage:
#    chmod +x scripts/run-pipeline.sh
#    ./scripts/run-pipeline.sh
#
# =============================================================================

set -e  # EXIT IMMEDIATELY if any command fails

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Track timing
PIPELINE_START=$(date +%s)

# Ensure we're in the project root
cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)

# ===========================================================================
# HELPER FUNCTIONS
# ===========================================================================

stage_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${CYAN}  STAGE: $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

pass() {
    echo -e "  ${GREEN}✓ PASSED${NC}: $1"
}

fail() {
    echo -e "  ${RED}✗ FAILED${NC}: $1"
    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}  PIPELINE FAILED at stage: $2${NC}"
    echo -e "${RED}  Fix the issue and run the pipeline again.${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 1
}

# ===========================================================================
# PIPELINE START
# ===========================================================================

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║      DOCKER & DEPLOYMENT PIPELINE - Starting...         ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Project:   ${PROJECT_DIR}"
echo -e "  Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "  Python:    $(python3 --version 2>/dev/null || python --version 2>/dev/null || echo 'NOT FOUND')"

# ===========================================================================
# STAGE 1: CHECK FILES
# ===========================================================================

stage_header "1/8 - CHECK (Verify Project Structure)"
echo "  Checking that all required files exist..."

REQUIRED_FILES=(
    "app/__init__.py"
    "app/inventory.py"
    "app/database.py"
    "app/cache.py"
    "app/api.py"
    "tests/unit/test_inventory.py"
    "tests/integration/test_api.py"
    "Dockerfile"
    "requirements.txt"
)

ALL_FOUND=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "    ${GREEN}✓${NC} $file"
    else
        echo -e "    ${RED}✗${NC} $file  ${RED}(MISSING!)${NC}"
        ALL_FOUND=false
    fi
done

if [ "$ALL_FOUND" = true ]; then
    pass "All source files present"
else
    fail "Missing required files" "CHECK"
fi

# ===========================================================================
# STAGE 2: INSTALL DEPENDENCIES
# ===========================================================================

stage_header "2/8 - DEPS (Install Dependencies)"
echo "  Installing Python dependencies from requirements.txt..."
echo ""

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

if $PYTHON_CMD -m pip install -r requirements.txt --quiet 2>&1; then
    pass "Dependencies installed successfully"
else
    fail "Failed to install dependencies" "DEPS"
fi

# ===========================================================================
# STAGE 3: UNIT TESTS
# ===========================================================================

stage_header "3/8 - UNIT TESTS (fast, no services needed)"
echo "  Running unit tests against inventory.py..."
echo ""

UNIT_START=$(date +%s)

if $PYTHON_CMD -m pytest tests/unit/ -v --tb=short 2>&1; then
    UNIT_END=$(date +%s)
    UNIT_TIME=$((UNIT_END - UNIT_START))
    echo ""
    pass "Unit tests passed (${UNIT_TIME}s)"
else
    UNIT_END=$(date +%s)
    UNIT_TIME=$((UNIT_END - UNIT_START))
    echo ""
    fail "Unit tests failed (${UNIT_TIME}s)" "UNIT TESTS"
fi

# ===========================================================================
# STAGE 4: CHECK DOCKER
# ===========================================================================

stage_header "4/8 - DOCKER CHECK (Is Docker installed?)"

DOCKER_AVAILABLE=false
if command -v docker &> /dev/null; then
    echo -e "    ${GREEN}✓${NC} Docker found: $(docker --version)"
    if docker info &> /dev/null; then
        echo -e "    ${GREEN}✓${NC} Docker daemon is running"
        DOCKER_AVAILABLE=true
    else
        echo -e "    ${YELLOW}!${NC} Docker is installed but the daemon is not running"
        echo -e "    ${YELLOW}  Start Docker Desktop and try again${NC}"
    fi
else
    echo -e "    ${YELLOW}!${NC} Docker is NOT installed"
    echo -e "    ${YELLOW}  Install Docker Desktop to run stages 5-8${NC}"
    echo -e "    ${YELLOW}  https://docs.docker.com/get-docker/${NC}"
fi

if [ "$DOCKER_AVAILABLE" = false ]; then
    echo ""
    echo -e "  ${YELLOW}Skipping Docker stages (4-8). Unit tests passed!${NC}"
    echo ""
    PIPELINE_END=$(date +%s)
    TOTAL_TIME=$((PIPELINE_END - PIPELINE_START))
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     ✓  PIPELINE PASSED (Docker stages skipped)  ✓      ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Total time: ${TOTAL_TIME}s"
    exit 0
fi

pass "Docker is available"

# ===========================================================================
# STAGE 5: BUILD DOCKER IMAGE
# ===========================================================================

stage_header "5/8 - BUILD (Build Docker Image)"
echo "  Building Docker image: inventory-api:local ..."
echo ""

if docker build -t inventory-api:local . 2>&1; then
    echo ""
    pass "Docker image built successfully"
else
    fail "Docker build failed" "BUILD"
fi

# ===========================================================================
# STAGE 6: RUN CONTAINER
# ===========================================================================

stage_header "6/8 - RUN (Start Container)"
echo "  Starting container on port 8080..."

# Stop any existing container with the same name
docker rm -f inventory-api-test 2>/dev/null || true

CONTAINER_ID=$(docker run -d --name inventory-api-test -p 8080:8080 inventory-api:local)
echo -e "    Container ID: ${CONTAINER_ID:0:12}"
echo "  Waiting for container to start..."
sleep 3

pass "Container started"

# ===========================================================================
# STAGE 7: HEALTH CHECK
# ===========================================================================

stage_header "7/8 - HEALTH CHECK (Test /health Endpoint)"
echo "  Sending GET request to http://localhost:8080/health ..."
echo ""

HEALTH_RESPONSE=$(curl -s http://localhost:8080/health 2>/dev/null || echo "FAILED")
echo "  Response: $HEALTH_RESPONSE"

if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo ""
    pass "Health check passed"
else
    echo ""
    echo -e "  ${YELLOW}Container logs:${NC}"
    docker logs inventory-api-test 2>&1 | tail -20
    docker rm -f inventory-api-test 2>/dev/null || true
    fail "Health check failed" "HEALTH CHECK"
fi

# ===========================================================================
# STAGE 8: CLEANUP
# ===========================================================================

stage_header "8/8 - CLEANUP (Stop & Remove Container)"
echo "  Stopping container..."
docker stop inventory-api-test > /dev/null 2>&1
docker rm inventory-api-test > /dev/null 2>&1
pass "Container cleaned up"

# ===========================================================================
# PIPELINE COMPLETE
# ===========================================================================

PIPELINE_END=$(date +%s)
TOTAL_TIME=$((PIPELINE_END - PIPELINE_START))

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║       ✓  PIPELINE PASSED SUCCESSFULLY!  ✓               ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Total time: ${TOTAL_TIME}s"
echo ""
echo -e "  ${BOLD}Pipeline Summary:${NC}"
echo -e "    ${GREEN}✓${NC} Check      - Project structure verified"
echo -e "    ${GREEN}✓${NC} Deps       - Dependencies installed"
echo -e "    ${GREEN}✓${NC} Unit Tests - All business logic working"
echo -e "    ${GREEN}✓${NC} Docker     - Docker is available"
echo -e "    ${GREEN}✓${NC} Build      - Docker image built"
echo -e "    ${GREEN}✓${NC} Run        - Container started"
echo -e "    ${GREEN}✓${NC} Health     - API responding correctly"
echo -e "    ${GREEN}✓${NC} Cleanup    - Container removed"
echo ""
