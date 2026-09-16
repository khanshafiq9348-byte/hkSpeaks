# Production Deployment Guide

## Production Architecture

```text
Load Balancer / Cloudflare CDN
       ↓
Next.js (Web Frontend)
       ↓
FastAPI (API Services)
       ↓
PostgreSQL 16 + Redis 7
       ↓
Celery / Async Background Workers
       ↓
Object Storage (Cloudflare R2 / AWS S3)
```

## Environment Variables
Set the following production variables in your secrets manager or container orchestration platform:

- `DATABASE_URL`: `postgresql+asyncpg://<user>:<password>@<host>:5432/<dbname>`
- `REDIS_URL`: `redis://<host>:6379/0`
- `SECRET_KEY`: High-entropy 64-character secret
- `STORAGE_PROVIDER`: `r2` or `s3`
- `STORAGE_ENDPOINT_URL`: Object storage endpoint
- `STORAGE_ACCESS_KEY_ID`: S3/R2 access key
- `STORAGE_SECRET_ACCESS_KEY`: S3/R2 secret key
- `STORAGE_BUCKET_NAME`: Storage bucket name
- `ELEVENLABS_API_KEY`: ElevenLabs key (if using ElevenLabs)
- `OPENAI_API_KEY`: OpenAI key (if using OpenAI)
- `STRIPE_SECRET_KEY`: Production Stripe secret key
- `STRIPE_WEBHOOK_SECRET`: Production Stripe webhook signing secret

## Container Deployment with Docker Compose
```bash
docker compose -f docker-compose.yml up -d --build
```
