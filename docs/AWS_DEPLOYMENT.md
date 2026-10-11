# AWS EC2 Deployment

This project is designed to run the complete stack on one EC2 instance for an academic/demo deployment.

AWS Free Tier eligibility and limits depend on the AWS account creation date and current AWS offers. Always use the AWS console label "Free tier eligible" and check your account's Free Tier/credits before launching. AWS documentation currently describes different Free Tier benefits for accounts created before and after July 15, 2025.

## 1. Launch EC2

Region:
\`ap-south-1\` (Mumbai)

For the operating system, use an Ubuntu or Amazon Linux image supported by your account's Free Tier offer.

Security group:
- SSH (22): your public IP only
- HTTP (80): 0.0.0.0/0
- HTTPS (443): add later if TLS is configured
- Do not open 3306/3307 or 5000 publicly

Create or select an EC2 key pair.

## 2. Connect

For Ubuntu, the default user is normally:

\`ubuntu\`

For Amazon Linux, it is normally:

\`ec2-user\`

Connect using SSH from your PC.

## 3. Bootstrap Docker

Copy and run:

\`scripts/ec2-bootstrap.sh\`

Then reconnect so the new Docker group membership is active.

## 4. Configure secrets

Edit:

\`~/online-examination-devops/.env\`

Set strong values for:

\`\`\`
MYSQL_ROOT_PASSWORD=
MYSQL_PASSWORD=
SECRET_KEY=
ADMIN_USERNAME=
ADMIN_EMAIL=
ADMIN_PASSWORD=
FRONTEND_HOST_PORT=80
\`\`\`

Also set:

\`CORS_ORIGINS=http://YOUR_EC2_PUBLIC_IP\`

For HTTPS later, replace this with the HTTPS origin.

## 5. Deploy

\`\`\`bash
cd ~/online-examination-devops
git checkout main
git pull origin main
docker compose -f docker/docker-compose.yml up -d --build
docker compose -f docker/docker-compose.yml exec backend python -m backend.create_admin
docker compose -f docker/docker-compose.yml ps
curl -fsS http://127.0.0.1/api/health
\`\`\`

Open:

\`http://YOUR_EC2_PUBLIC_IP\`

## 6. GitHub Actions deployment

Add repository secrets:

\`\`\`
EC2_HOST
EC2_USER
EC2_SSH_KEY
\`\`\`

The deploy workflow updates the EC2 working tree and runs Docker Compose.

## 7. Monitoring and troubleshooting

\`\`\`bash
docker compose -f docker/docker-compose.yml ps
docker compose -f docker/docker-compose.yml logs --tail=100 backend
docker compose -f docker/docker-compose.yml logs --tail=100 frontend
docker compose -f docker/docker-compose.yml logs --tail=100 mysql
curl -fsS http://127.0.0.1/api/health
df -h
free -h
\`\`\`

For a stronger production setup, add CloudWatch Agent/log shipping and HTTPS with a domain + TLS.

## Cost safety

Stop or terminate resources when they are no longer needed, and regularly inspect AWS Billing/Free Tier usage. AWS notes that EC2 usage can incur charges when the usage is outside your applicable Free Tier/credits.
