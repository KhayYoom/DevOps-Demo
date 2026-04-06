# Docker & Deployment Lab - Hands-On Guide

## What You'll Learn

By completing this lab, you will understand:
- How to run service containers (Postgres, Redis) alongside your GitHub Actions jobs
- How health checks ensure services are ready before tests run
- How to build Docker images and push to GitHub Container Registry (GHCR)
- How to use docker/metadata-action for automated tagging
- How to verify published images in a workflow
- How multi-stage Docker builds produce smaller production images

## Prerequisites

- Completed lab-pipeline (CI/CD Pipeline basics)
- Docker Desktop installed (for local testing)
- Python 3.12+
- Estimated time: **2 hours** (Lab 7: ~50 min, Lab 8: ~50 min)

```bash
# Check prerequisites
python --version        # Should be 3.12+
docker --version        # Docker Desktop
docker-compose --version  # Comes with Docker Desktop
```

---

## Project Structure

```
lab-docker-deploy/
│
├── app/                              THE APPLICATION
│   ├── __init__.py
│   ├── inventory.py                  Core business logic (pure Python)
│   ├── database.py                   PostgreSQL operations (psycopg2)
│   ├── cache.py                      Redis caching layer (redis-py)
│   └── api.py                        HTTP API server (endpoints)
│
├── tests/                            THE TESTS
│   ├── unit/
│   │   └── test_inventory.py         Unit tests (no DB needed!)
│   └── integration/
│       ├── test_database.py          Postgres tests (skipped if no DB)
│       ├── test_cache.py             Redis tests (skipped if no Redis)
│       └── test_api.py               Full API integration tests
│
├── scripts/                          PIPELINE RUNNERS
│   ├── run-pipeline.sh               Local pipeline (Linux/WSL/Mac)
│   └── run-pipeline.bat              Local pipeline (Windows CMD)
│
├── .github/workflows/
│   ├── lab7-service-containers.yml   Service containers workflow
│   └── lab8-docker-publish.yml       Docker build & publish workflow
│
├── Dockerfile                        Multi-stage Docker build
├── docker-compose.yml                Local dev environment
├── .dockerignore                     Files excluded from Docker image
├── requirements.txt                  Python dependencies
├── pytest.ini                        Test configuration
├── .gitignore                        Git ignore rules
└── LAB-GUIDE.md                      This file!
```

---

## How to Run Locally

### Option 1: Unit tests only (no Docker needed)

```bash
cd lab-docker-deploy
pip install -r requirements.txt
python -m pytest tests/unit/ -v
```

### Option 2: Full stack with docker-compose

```bash
cd lab-docker-deploy
docker-compose up --build -d

# Run integration tests against the real services
DATABASE_URL=postgresql://devuser:devpass@localhost:5432/inventory \
REDIS_URL=redis://localhost:6379 \
python -m pytest tests/ -v

# Clean up
docker-compose down
```

### Option 3: Run the pipeline script

```bash
# Linux/Mac/WSL
chmod +x scripts/run-pipeline.sh
./scripts/run-pipeline.sh

# Windows CMD
scripts\run-pipeline.bat
```

---

## Understanding the Application

### Inventory Manager (`app/inventory.py`)

The core business logic. Products are stored in a Python dictionary so that
**unit tests can run without any database**. This is a deliberate design
choice: separate logic from infrastructure.

Key methods: `add_product()`, `get_product()`, `update_stock()`,
`remove_product()`, `search_products()`, `get_low_stock()`,
`get_inventory_value()`.

### Database Layer (`app/database.py`)

Wraps psycopg2 to provide CRUD operations against PostgreSQL. This layer
is used by integration tests that connect to a real Postgres instance
(either via docker-compose locally or via a service container in CI).

### Cache Layer (`app/cache.py`)

Wraps redis-py to cache product data with JSON serialization and TTL
support. Integration tests connect to a real Redis instance.

### API Server (`app/api.py`)

A simple HTTP API using Python's built-in `http.server`. It uses the
InventoryManager for business logic and optionally connects to Postgres
and Redis when `DATABASE_URL` and `REDIS_URL` environment variables are set.

---

## Lab 7: Service Containers (45-55 min)

### Objective

Run PostgreSQL and Redis as **service containers** in GitHub Actions so
that integration tests can connect to real databases during CI.

### Background: What Are Service Containers?

Service containers are Docker containers that GitHub Actions starts
**automatically** alongside your job. They run on the same Docker network
as your job's container (or as localhost-accessible containers when
running directly on the VM).

```yaml
services:
  postgres:
    image: postgres:16
    ports:
      - 5432:5432       # Maps container port to host port
    options: >-
      --health-cmd "pg_isready"   # How to check if it's ready
      --health-interval 10s       # Check every 10 seconds
      --health-timeout 5s         # Timeout per check
      --health-retries 5          # Give up after 5 failures
```

**Health checks are critical.** Without them, your tests might start
running before Postgres has finished initializing, causing
"connection refused" errors.

**Important:** Service containers only work on **Linux runners**
(`ubuntu-latest`). They do NOT work on `windows-latest` or `macos-latest`.

**Port mapping:** When your job runs directly on the VM (not in a
container), you access service containers via `localhost:{port}`.

### Instructions

**Step 1:** Examine the application code

```bash
# Look at the business logic (no DB dependency)
cat app/inventory.py

# Look at the database layer
cat app/database.py

# Look at the cache layer
cat app/cache.py
```

**Step 2:** Run unit tests locally (no services needed)

```bash
python -m pytest tests/unit/ -v
```

Notice: all tests pass without any database or Redis. The InventoryManager
uses an in-memory dict.

**Step 3:** Read the workflow file

```bash
cat .github/workflows/lab7-service-containers.yml
```

Pay attention to:
- The `services:` section (defines Postgres and Redis containers)
- The `options:` with health check commands
- The `env:` section on the integration test step (passes DATABASE_URL and REDIS_URL)
- The two jobs: `integration-tests` (with services) and `unit-tests-only` (without)

**Step 4:** Push to GitHub and watch the workflow run

```bash
git add .
git commit -m "feat: add service containers lab"
git push
```

Go to your repo's **Actions** tab. You should see the "Lab 7 - Service Containers"
workflow running.

**Step 5:** Observe the service container startup

In the workflow logs, look for lines like:
```
Creating service container for postgres...
Waiting for service container postgres to be healthy...
Service container postgres is healthy
```

The services start BEFORE your steps run. GitHub Actions waits for all
health checks to pass.

**Step 6:** Check the health check logs

Click on the "Wait for services to be ready" step. You should see
successful `pg_isready` and `redis-cli ping` checks.

**Step 7:** Verify integration tests pass

Click on "Run integration tests". The database tests should connect
to the real Postgres, and the cache tests should connect to the real Redis.

**Step 8 (Optional):** Run locally with docker-compose

```bash
docker-compose up -d
DATABASE_URL=postgresql://devuser:devpass@localhost:5432/inventory \
REDIS_URL=redis://localhost:6379 \
python -m pytest tests/integration/ -v
docker-compose down
```

### Checkpoint Questions

1. **What runner OS is required for service containers?**
   `ubuntu-latest` (Linux). Service containers do NOT work on Windows or macOS runners.

2. **What happens if you remove the health check options?**
   Your test steps might start before the database is ready, causing
   "connection refused" errors. The health check ensures GitHub Actions
   waits until the service is accepting connections.

3. **How do you access the service from your test code?**
   Via `localhost:{port}` when running directly on the VM. The `ports:`
   mapping in the workflow maps the container's port to the host.

4. **Can you run service containers on self-hosted runners?**
   Yes, but the runner must have Docker installed and configured.

### Break It!

1. **Remove the health check** from the Postgres service. Do the
   integration tests fail with "connection refused"?

2. **Use a wrong password** in the DATABASE_URL environment variable.
   What error do you see in the test output?

3. **Try `runs-on: windows-latest`** instead of `ubuntu-latest`.
   What error does GitHub Actions show?

4. **Change the Postgres version** from `16` to `15`. Do the tests
   still pass? (They should -- the SQL is basic.)

---

## Lab 8: Docker Build & Publish (45-55 min)

### Objective

Build a Docker image for the Inventory API and push it to **GitHub
Container Registry (GHCR)** using a multi-stage Dockerfile.

### Background: GHCR vs Docker Hub

| Feature | GHCR (ghcr.io) | Docker Hub |
|---------|----------------|------------|
| Auth | GITHUB_TOKEN (free) | Separate account |
| Pricing | Free for public repos | Rate-limited free tier |
| Integration | Native to GitHub | Third-party |
| URL | ghcr.io/owner/image | docker.io/user/image |

GHCR is ideal for GitHub projects because `GITHUB_TOKEN` provides
authentication automatically -- no secrets to configure.

### Background: GITHUB_TOKEN for GHCR Auth

The `GITHUB_TOKEN` is automatically created by GitHub Actions for every
workflow run. To push to GHCR, you need:

```yaml
permissions:
  contents: read
  packages: write    # THIS grants push access to GHCR
```

### Background: docker/metadata-action Tagging

The `docker/metadata-action` automatically generates Docker image tags
from your git context:

| Git event | Generated tag |
|-----------|---------------|
| Push to main | `latest`, `main` |
| Push commit abc1234 | `abc1234` |
| Tag v1.2.3 | `1.2.3`, `1.2` |

This means you never have to manually manage Docker tags!

### Background: Multi-Stage Docker Builds

The Dockerfile uses two stages:

```dockerfile
# Stage 1: Install dependencies (large image with build tools)
FROM python:3.12-slim AS builder
RUN pip install --prefix=/install -r requirements.txt

# Stage 2: Copy only what's needed (small production image)
FROM python:3.12-slim
COPY --from=builder /install /usr/local
COPY app/ ./app/
```

The final image only contains the runtime -- no pip, no build tools,
no source code for tests. This produces a smaller, more secure image.

### Background: .dockerignore

Just like `.gitignore` keeps files out of git, `.dockerignore` keeps files
out of the Docker build context. This makes builds faster and images smaller.

### Instructions

**Step 1:** Examine the Dockerfile

```bash
cat Dockerfile
```

Notice the two `FROM` statements (multi-stage build). The `builder` stage
installs dependencies, and the runtime stage copies only the installed
packages and the app code.

**Step 2:** Build locally

```bash
docker build -t inventory-api .
```

Watch the output -- you'll see both stages execute.

**Step 3:** Run locally

```bash
docker run -p 8080:8080 inventory-api

# In another terminal:
curl http://localhost:8080/health
curl http://localhost:8080/products
```

The API works without Postgres/Redis -- it falls back to the in-memory
InventoryManager.

**Step 4:** Read the workflow file

```bash
cat .github/workflows/lab8-docker-publish.yml
```

Pay attention to:
- Three jobs: `test` -> `build-and-push` -> `verify`
- The `permissions:` block (packages: write)
- `docker/login-action` for GHCR authentication
- `docker/metadata-action` for automatic tagging
- `docker/build-push-action` for building and pushing
- The `verify` job that pulls and tests the published image

**Step 5:** Push to GitHub and watch the workflow

```bash
git add .
git commit -m "feat: add Docker publish workflow"
git push
```

Watch the "Lab 8 - Docker Build & Publish" workflow in the Actions tab.

**Step 6:** Check your published image

After the workflow completes, go to your repository page on GitHub.
Look for the **Packages** section in the right sidebar. You should see
`inventory-api` listed there.

**Step 7:** Create a version tag

```bash
git tag v1.0.0
git push origin v1.0.0
```

This triggers the workflow again. Watch the tags that are generated.

**Step 8:** Observe semver tags

After the tagged workflow completes, check the package versions.
You should see tags like:
- `1.0.0` (full version)
- `1.0` (major.minor)
- `latest`
- The short git SHA

### Checkpoint Questions

1. **What permission is needed to push to GHCR?**
   `packages: write` in the job's `permissions` block.

2. **What does docker/metadata-action do?**
   It generates Docker image tags and labels automatically from git context
   (branch, tag, SHA). No manual tag management needed.

3. **How are tags generated from git tags?**
   A git tag like `v1.2.3` produces Docker tags `1.2.3` and `1.2`
   (via the `semver` pattern). The `v` prefix is stripped automatically.

4. **What is the verify job testing?**
   It pulls the just-published image from GHCR, runs it as a container,
   and tests the `/health` endpoint with curl to confirm the image works.

### Break It!

1. **Remove `packages: write`** from the permissions block. What error
   do you see when the workflow tries to push to GHCR?

2. **Break the Dockerfile** -- change `FROM python:3.12-slim` to
   `FROM nonexistent:latest`. What happens during the build step?

3. **Remove `.dockerignore`** and rebuild. What extra files get included
   in the Docker image? (Hint: check the build context size.)

---

## Key Takeaways

```
1. SERVICE CONTAINERS:
   - Docker containers that run alongside your CI job
   - Perfect for integration testing with real databases
   - Health checks prevent "connection refused" race conditions
   - Linux runners only (ubuntu-latest)

2. DOCKER BUILD & PUBLISH:
   - GHCR uses GITHUB_TOKEN (no extra secrets needed)
   - docker/metadata-action automates tagging from git context
   - Multi-stage builds produce small, secure images
   - Verify jobs confirm published images actually work

3. SEPARATION OF CONCERNS:
   - Business logic (inventory.py) has NO infrastructure deps
   - Unit tests run fast without any services
   - Integration tests use real Postgres/Redis via service containers
   - This architecture enables reliable, layered testing

4. THE TESTING PYRAMID IN ACTION:
   - Unit tests (fast, many)     -> test business logic
   - Integration tests (slower)  -> test with real databases
   - Verify job (end-to-end)     -> test the published Docker image
```

---

## Quick Reference

```bash
# Run unit tests only (no Docker, no DB)
python -m pytest tests/unit/ -v

# Run all tests with docker-compose services
docker-compose up -d
DATABASE_URL=postgresql://devuser:devpass@localhost:5432/inventory \
REDIS_URL=redis://localhost:6379 \
python -m pytest -v
docker-compose down

# Build Docker image
docker build -t inventory-api .

# Run container
docker run -p 8080:8080 inventory-api

# Run with full stack
docker-compose up --build

# Test the API
curl http://localhost:8080/health
curl http://localhost:8080/products
curl -X POST http://localhost:8080/products \
  -H "Content-Type: application/json" \
  -d '{"name": "Widget", "price": 9.99, "quantity": 100}'

# Run the local pipeline
./scripts/run-pipeline.sh       # Linux/Mac/WSL
scripts\run-pipeline.bat        # Windows CMD

# Create a version tag
git tag v1.0.0
git push origin v1.0.0
```

---

## What's Next?

Continue to **lab-custom-actions** to learn how to create your own
reusable GitHub Actions (composite actions and JavaScript actions).
