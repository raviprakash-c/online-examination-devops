# DevOps Implementation Map

| Concept | Implementation |
|---|---|
| Version control | Git |
| Remote source control | GitHub |
| Branching | process-1-core-backend, process-2-full-project |
| Code review | Pull Request #1 |
| Continuous Integration | GitHub Actions |
| Automated testing | pytest |
| Static syntax verification | compileall + node --check |
| Containerization | Docker |
| Multi-container setup | Docker Compose |
| Configuration management | environment variables |
| Secret protection | .env ignored from Git |
| Health checks | Docker healthcheck + /api/health |
| Reverse proxy | Nginx |
| Cloud deployment | AWS EC2 |
| Deployment automation | GitHub Actions deploy workflow |
| Application logging | Gunicorn/Flask stdout |
| Infrastructure troubleshooting | docker compose ps/logs + health endpoint |
| Rollback | Git branch / previous Git commit |
| Collaboration | GitHub branches + PR |

## CI flow

Developer -> branch -> commit -> push -> PR -> GitHub Actions -> tests/build -> merge

## CD flow

main -> GitHub Actions -> SSH -> EC2 -> git reset to origin/main -> docker compose build/up -> health check

## Container responsibilities

MySQL:
- Persistent relational data

Backend:
- Flask REST API
- Authentication
- Business logic
- Evaluation

Frontend:
- Nginx static hosting
- Reverse proxy for /api/

## Reliability

The backend waits for a healthy MySQL container before startup.
The backend exposes /api/health for readiness checks.
The frontend depends on the healthy backend container.
Containers use restart policies.

## Security

Passwords are stored with Werkzeug password hashing.
Sessions use HTTPOnly cookies.
Security response headers are added by the API.
Production passwords and SECRET_KEY belong in environment variables.
