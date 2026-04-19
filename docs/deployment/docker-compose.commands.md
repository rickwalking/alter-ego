# Build and run all services
docker compose up --build

# Run in detached mode
docker compose up -d --build

# Stop all services
docker compose down

# View logs
docker compose logs -f backend

# Run backend tests
docker compose run --rm backend uv run pytest

# Run frontend build check
docker compose run --rm frontend npm run build
