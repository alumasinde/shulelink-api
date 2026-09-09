$ErrorActionPreference = "Stop"

Write-Host "Starting ShuleLink development stack with database migrations..." -ForegroundColor Cyan

docker compose -f docker-compose.dev.yml -f docker-compose.dev.migrations.yml up --build $args
