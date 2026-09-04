# 🚀 Deployment Guide

This document covers deploying the AI Council to a production environment.

## Option 1: Docker Compose (Self-Hosted)

**Best for**: Development, staging, or small-scale production.

1.  Ensure `.env` is fully configured.
2.  Run:
    ```bash
    docker-compose up -d --build
    ```
3.  Access at `http://your-server-ip:3000`.
4.  Set up a reverse proxy (Nginx) to handle SSL termination.

**Nginx configuration snippet**:
```nginx
server {
    listen 443 ssl;
    server_name ai-council.yourdomain.com;
    ssl_certificate /etc/letsencrypt/live/...;
    ssl_certificate_key ...;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
    }
}
```

## Option 2: Vercel + AWS (Cloud-Native)

**Frontend** (Vercel):
1.  Push code to GitHub.
2.  Connect repository to Vercel.
3.  Set environment variables (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WEBSOCKET_URL`).
4.  Deploy automatically on push.

**Backend** (AWS ECS Fargate):
1.  Containerize the FastAPI backend (Dockerfile provided).
2.  Push image to AWS ECR.
3.  Create ECS cluster and task definition (memory: 2GB, CPU: 1 vCPU).
4.  Attach an Application Load Balancer (ALB) with WebSocket support.
5.  Set environment variables via AWS Secrets Manager (for secrets).

**Database** (AWS RDS):
1.  Provision PostgreSQL 15+ instance (t3.micro for dev, t3.medium for prod).
2.  Enable automated backups.
3.  Update `DATABASE_URL` in ECS task definition.

**LMArenaBridge** (AWS ECS):
1.  Run as a separate service.
2.  Use the same load balancer but expose a different port.
3.  Store the auth token in Secrets Manager.

## Option 3: Single VM (DigitalOcean / Linode)

1.  Provision an Ubuntu 22.04 VM.
2.  Install Docker and Docker Compose.
3.  Clone the repository.
4.  Set up `.env`.
5.  Run `docker-compose up -d`.
6.  Install Certbot for HTTPS.

## Monitoring & Logging

- **Logs**: `docker-compose logs -f` or use AWS CloudWatch / DataDog.
- **Metrics**: Expose Prometheus metrics at `/metrics` (FastAPI endpoint).
- **Health Checks**: Configure ELB to hit `/health` every 30 seconds.

## Backup Strategy

- **Database**: Daily `pg_dump` stored in S3 bucket (retention: 30 days).
- **Configuration**: Store `.env` in a secure vault (not in repo).

## Rollback Procedure

1.  If using Docker: revert to a previous image tag.
2.  If using Vercel: revert deployment from dashboard.
3.  Database rollback: use point-in-time recovery (RDS) or restore from backup.
