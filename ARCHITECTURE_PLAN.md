## ReactJS + FastAPI Single-Codebase Architecture Plan

### Goal

Single primary codebase for Web + hybrid mobile (Android/iOS) using ReactJS, with a FastAPI backend that is production‑grade, scalable, and microservice‑ready, while keeping code volume reasonable and UI modern/elegant.

---

## Overall Architecture

- **Client layer**
  - **Web**: React SPA (or Next.js) as the primary UI.
  - **Mobile (Android/iOS)**: Same React app wrapped via **Capacitor** to ship as native apps.
- **Backend layer**
  - **Edge / Gateway**: API Gateway / Ingress.
  - **FastAPI services**: Modular monolith at first, evolving into microservices (auth, user, billing, content, notifications).
- **Shared services**
  - Auth, logging/metrics/tracing, message broker, CI/CD, infrastructure as code.

---

## Client Stack (React + Hybrid Mobile)

### Core technologies

- **Language**: TypeScript
- **Framework**:
  - React for UI.
  - Next.js (recommended) for SSR/SSG + SPA‑like UX, or Vite+React if you prefer pure SPA.
- **Hybrid wrapper**:
  - Capacitor to package the web app into Android/iOS shells and access native APIs.

### UI/UX & state

- **UI toolkit**:
  - Tailwind CSS + Headless UI or Chakra UI for fast, elegant, modern components.
- **Design system**:
  - Central design tokens (colors, typography, spacing, radii, shadows).
  - Shared `ui/` components: Button, Card, Input, Modal, etc.
- **State management**:
  - React Query (TanStack Query) for server state (API data, caching, retries).
  - Lightweight global state with Zustand or Redux Toolkit.

### Project structure (client)

- `apps/web` – Next.js (or React+Vite) app.
- `apps/mobile` – Capacitor shell that loads the built web app.
- `packages/ui` – Shared design system components.
- `packages/core` – Shared types, validation, utilities.
- `packages/api` – Typed API client (generated from OpenAPI) used by React.

### Client build & deployment

- **Web**:
  - Build static or server‑rendered app and deploy to:
    - S3 + CloudFront, or
    - Vercel (ideal for Next.js).
- **Mobile**:
  - Capacitor builds native projects:
    - Android: AAB/APK → Google Play.
    - iOS: IPA → App Store.
- **CI/CD (client)**:
  - GitHub Actions:
    - Lint, test, build React.
    - Build Capacitor Android/iOS bundles.
  - Fastlane for automated store uploads.

---

## Backend Stack (FastAPI Microservice‑Ready)

### Core technologies

- **Language**: Python 3.12+
- **Framework**: FastAPI (async, type‑hinted, automatic OpenAPI docs).
- **Server**:
  - Uvicorn (possibly behind Gunicorn) in production.

### Architecture style

- **Phase 1 – Modular monolith**:
  - Separate routers and domain modules in one FastAPI app:
    - `auth`, `users`, `billing`, `content`, `notifications`, `files`.
- **Phase 2 – Microservices**:
  - Split each domain into its own FastAPI service if needed, re‑using shared libraries and patterns.

### Services & domains

- **Auth service**
  - JWT issuance/verification, refresh tokens, password reset, social login if needed.
- **User service**
  - User profiles, settings, preferences.
- **Billing service**
  - Plans, subscriptions, payments (Stripe), webhooks.
- **Content/domain service**
  - Core business entities (e.g., products, posts, tasks, etc.).
- **Notification service**
  - Email (SES/SendGrid), push via FCM/APNs (through Capacitor plugins), in‑app messages.
- **File service**
  - File uploads, S3 storage, signed URLs for secure access.

### Data & persistence

- **Primary DB**: PostgreSQL (managed: AWS RDS, Cloud SQL, etc.).
- **ORM / DB layer**:
  - SQLAlchemy 2.x + Alembic for migrations.
- **Schemas & validation**:
  - Pydantic models for request/response DTOs; optionally generate TS types from these.
- **Caching**:
  - Redis for hot data, sessions, rate limiting.
- **Search** (optional):
  - OpenSearch/Elasticsearch if you need full‑text or advanced search.

### Async & background work

- **Message broker / queue**:
  - RabbitMQ or Kafka for events (user‑created, payment‑succeeded, etc.).
- **Task processing**:
  - Celery (with Redis/RabbitMQ) or RQ for background jobs (emails, PDFs, imports).

### Auth & security

- **Auth model**:
  - JWT access tokens + refresh tokens.
  - Optional OIDC integration with Auth0 / Keycloak if you want an external IdP.
- **API security**:
  - FastAPI dependencies for auth & role checks on routes.
  - Rate limiting at gateway (NGINX/Kong + Redis).

---

## Infrastructure, Observability, and CI/CD

### Repo & tooling

- **Monorepo**:
  - `apps/web` – React/Next.js.
  - `apps/mobile` – Capacitor shell.
  - `services/auth`, `services/users`, `services/billing`, `services/content`, etc. – FastAPI.
  - `packages/shared-python` – shared FastAPI utilities, Pydantic models.
  - `packages/shared-ts` – generated API clients/types.
  - `infra/` – Terraform, Helm charts, Kubernetes manifests.
- **Build orchestration**:
  - Turborepo or Nx for JS/TS parts.
  - Python managed with poetry or pip-tools, wired into CI.

### Containerization & orchestration

- **Containers**:
  - Docker images for each FastAPI service and the web app.
- **Orchestration**:
  - Kubernetes (EKS/GKE/AKS).
  - Ingress + API gateway:
    - NGINX Ingress Controller or Kong.
- **Config & secrets**:
  - K8s ConfigMaps and Secrets.
  - Optional external secrets manager (AWS Secrets Manager, HashiCorp Vault).

### Observability

- **Logging**:
  - Structured JSON logs (FastAPI with stdlib logging/loguru).
  - Aggregation with ELK (Elasticsearch, Logstash, Kibana) or Loki + Grafana.
- **Metrics**:
  - Prometheus scraping app and infrastructure metrics.
  - Grafana dashboards (latency, error rate, throughput, DB metrics).
- **Tracing**:
  - OpenTelemetry in FastAPI and gateway.
  - Jaeger or Tempo as trace backend.

### CI/CD

- **CI**:
  - GitHub Actions / GitLab CI pipelines to:
    - Run tests (React + pytest).
    - Lint/format (ESLint/Prettier, black/ruff).
    - Build Docker images.
- **CD**:
  - Push images to ECR/GCR/ACR.
  - Deploy to Kubernetes via ArgoCD or Flux (GitOps).
  - Separate workflows:
    - Web deploys.
    - Backend service rollouts (blue/green/canary).
    - Mobile builds + Fastlane for store distribution.

---

## Scalability, Performance, and Productivity

- **Scalability**
  - Stateless FastAPI services scaled horizontally with K8s HPA.
  - PostgreSQL read replicas and partitioning for heavier workloads.
  - API + Redis caching for hot endpoints and rate‑limited routes.
- **Performance**
  - Async endpoints, connection pooling, proper indexes.
  - Client‑side caching and pagination with React Query.
  - Asset optimization and lazy‑loading in React/Next.js.
- **Productivity / less coding**
  - FastAPI + Pydantic for concise APIs and automatic docs.
  - OpenAPI‑driven TS client generation to avoid duplicate typing.
  - Reusable design system and layout components in React.

---

## Development Workflow

- **Branching & review**
  - Short‑lived feature branches and pull requests.
- **Code quality**
  - ESLint + Prettier (TS), black + isort + ruff (Python).
  - Pre‑commit hooks.
- **Testing**
  - Unit tests: Jest/RTL (frontend), pytest (backend).
  - Integration tests for FastAPI (test DB).
  - Contract tests between frontend and backend using OpenAPI specs.