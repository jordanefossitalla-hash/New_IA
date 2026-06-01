# Document Ingestion Platform

Plateforme d'ingestion de documents prête pour la production.

## Stack

- Python 3.12
- FastAPI
- PostgreSQL + pgvector
- SQLAlchemy 2.0
- Alembic
- Redis
- Celery
- Docker Compose

## Architecture

- Clean Architecture
- Structure modulaire
- Injection de dependances via `dependency-injector`
- Gestion de configuration via variables d'environnement (`pydantic-settings`)
- Logging structure (JSON ou texte)
- Endpoint de sante: `GET /api/v1/health`
- Services separes: `api` et `worker`

## Structure

```text
.
|-- alembic/
|-- scripts/
|-- src/app/
|   |-- application/
|   |-- core/
|   |-- domain/
|   |-- infrastructure/
|   |-- presentation/
|   |-- shared/
|   `-- worker/
|-- .env.example
|-- alembic.ini
|-- docker-compose.yml
|-- Dockerfile.api
|-- Dockerfile.worker
|-- logging.yaml
`-- pyproject.toml
```

## Demarrage

1. Copier `.env.example` vers `.env`
2. Lancer `docker compose up --build`
