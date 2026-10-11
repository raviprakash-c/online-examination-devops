# Online Examination System – DevOps Mini Project

A full-stack Online Examination System built for a DevOps mini project using Flask, MySQL, Docker, GitHub Actions, and AWS EC2.

## Features

### Student
- Register and login
- View available exams
- Start an exam
- Server-controlled exam timer
- MCQ answer submission
- Automatic evaluation
- Pass/fail result
- Previous results

### Admin
- Login using a provisioned admin account
- Create, edit, and delete exams
- Add, edit, and delete questions
- View student results
- Dashboard summary

### DevOps
- Git branch based development
- GitHub repository
- Pull requests
- Automated CI with GitHub Actions
- Unit/API tests with pytest
- Dockerized backend and frontend
- Docker Compose orchestration
- Health checks
- Environment variables for configuration
- AWS EC2 deployment workflow
- Production-oriented logging and security headers

## Architecture

Browser -> Nginx frontend -> Flask API -> MySQL

Git -> GitHub -> GitHub Actions CI -> Docker build -> main -> EC2 deployment

## Repository structure

\`\`\`
.
├── backend/
│   ├── app.py
│   ├── db.py
│   ├── create_admin.py
│   ├── requirements.txt
│   └── .env.example
├── database/
│   └── schema.sql
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── nginx.conf
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── scripts/
│   └── ec2-bootstrap.sh
├── tests/
│   └── test_backend.py
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
└── docs/
    ├── API.md
    ├── AWS_DEPLOYMENT.md
    └── DEVOPS.md
\`\`\`

## Local setup

Prerequisites:
- Python 3.10+
- Docker Desktop
- Git

Activate the virtual environment:

\`\`\`powershell
.\\venv\\Scripts\\Activate.ps1
\`\`\`

Run backend tests:

\`\`\`powershell
python -m pytest -q
\`\`\`

Start the complete Docker stack from the repository root:

\`\`\`powershell
docker compose -f docker/docker-compose.yml up -d --build
\`\`\`

Open:

\`\`\`
http://localhost:8080
\`\`\`

API health:

\`\`\`
http://localhost:8080/api/health
\`\`\`

Database is also exposed for local inspection at:

\`\`\`
Host: 127.0.0.1
Port: 3307
Database: online_exam
User: examuser
\`\`\`

View container status:

\`\`\`powershell
docker compose -f docker/docker-compose.yml ps
\`\`\`

View logs:

\`\`\`powershell
docker compose -f docker/docker-compose.yml logs -f
\`\`\`

Stop the stack:

\`\`\`powershell
docker compose -f docker/docker-compose.yml down
\`\`\`

## Provision the admin account

The backend provides a secure runtime provisioning script. Set these environment variables and run:

\`\`\`powershell
$env:ADMIN_USERNAME="admin"
$env:ADMIN_EMAIL="admin@example.com"
$env:ADMIN_PASSWORD="ChangeThisPassword!"
python -m backend.create_admin
\`\`\`

When using Docker Compose, place the values in the ignored root \`.env\` file and run:

\`\`\`powershell
docker compose -f docker/docker-compose.yml exec backend python -m backend.create_admin
\`\`\`

## CI/CD

Every push to \`main\` and \`process-*\` branches runs:

1. Python environment setup
2. Dependency installation
3. Backend compilation check
4. pytest test suite
5. Frontend JavaScript syntax check
6. Docker Compose validation
7. Backend Docker image build
8. Frontend Docker image build

The deployment workflow runs after pushes to \`main\` or by manual dispatch. It connects to an EC2 instance over SSH, updates the repository, rebuilds the Docker stack, provisions the admin account, and checks the deployed application.

Required GitHub Actions secrets:

\`\`\`
EC2_HOST
EC2_USER
EC2_SSH_KEY
\`\`\`

The EC2 instance itself should contain a secure \`.env\` with production passwords and a long random \`SECRET_KEY\`.

## Important security notes

- Never commit \`.env\` files or private keys.
- Use a strong production \`SECRET_KEY\`.
- Keep SSH port 22 restricted to your own IP where possible.
- Do not expose MySQL port 3306/3307 to the public internet.
- Keep backend port 5000 private on AWS; expose the frontend on port 80.
- Replace the development default credentials before deployment.

## Demo flow

1. Open the web application.
2. Register a student.
3. Log in as student.
4. Open an available exam.
5. Answer MCQs and submit.
6. Confirm automatic result calculation.
7. Log in as admin.
8. Create/edit/delete exams and questions.
9. Review student results and dashboard statistics.
10. Show GitHub Actions CI.
11. Show Docker Compose containers.
12. Show the AWS EC2 deployment.

## DevOps mapping

Git = version control

GitHub = remote repository and pull requests

GitHub Actions = continuous integration and deployment

pytest = automated tests

Docker = packaging and environment consistency

Docker Compose = multi-container orchestration

Environment variables = configuration and secret separation

Health checks = service availability validation

AWS EC2 = cloud deployment

Nginx = frontend server and reverse proxy

Application stdout logs = container-friendly logging

See \`docs/DEVOPS.md\` and \`docs/AWS_DEPLOYMENT.md\` for the full explanation.
