# Docker

Docker is an infrastructure layer, not a second application configuration system. The FastAPI application continues to consume the same environment contract defined by `backend/app/core/config.py`.

## Development

1. Copy `docker/mysql.env.example` to `docker/mysql.env` and set local passwords.
2. Copy `backend/.env.docker.example` to `backend/.env.docker` if you want to customize it.
3. Update `docker-compose.dev.yml` to reference your real local Docker env file when needed.
4. Start the stack:

```bash
docker compose -f docker-compose.dev.yml up --build
```

The API is exposed on port 8000, MariaDB on 3306, and Redis on 6379. Inside Docker, the API reaches MariaDB at `mysql` and Redis at `redis`; it must not use `localhost` for those services.

## Production-like compose

`docker-compose.yml` provides the API, MariaDB and Redis services with persistent volumes, health checks, a non-root API user, a read-only API filesystem, dropped Linux capabilities, and `no-new-privileges`.

Before using it, provide a real `backend/.env` containing production-appropriate values. The application configuration validator remains authoritative and will refuse unsafe production configuration.

## Important

Do not commit `backend/.env`, `backend/.env.docker`, `docker/mysql.env`, certificates, private keys, or other secrets. Templates ending in `.example` are safe configuration contracts only and contain placeholders.

For real production, the database and Redis should normally be managed infrastructure rather than casually colocated application containers. Docker gives ShuleLink reproducible application packaging without weakening the existing environment separation.
