# ShuleLink

ShuleLink is a multi-tenant school management SaaS for schools in Kenya.

## Phase 1 — Foundation

Phase 1 establishes the production-oriented application foundation:

- FastAPI backend
- Vue 3 frontend with Bootstrap 5
- MySQL with raw SQL migrations
- API versioning under `/api/v1`
- Environment-based configuration
- Structured application logging
- Consistent API error responses
- CORS and trusted-host configuration
- Health/readiness endpoints
- Tenant-aware architecture hooks for later phases
- Basic automated backend tests

## Repository Layout

```text
backend/     FastAPI application and SQL migrations
frontend/    Vue 3 application
```

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Copy `.env.example` to `.env` and configure MySQL before starting the API.

## API

- Health: `GET /api/v1/health`
- Readiness: `GET /api/v1/health/ready`
- OpenAPI: `/docs`

The Phase 1 API intentionally contains no school business domain or user identity data. Those are introduced in later phases.
