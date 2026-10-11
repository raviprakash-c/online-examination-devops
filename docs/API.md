# API Reference

Base URL when using the complete Docker stack:

\`http://localhost:8080/api\`

## Authentication

### Register
\`POST /auth/register\`

Payload:
\`\`\`json
{
  "username": "student1",
  "email": "student1@example.com",
  "password": "StrongPass123"
}
\`\`\`

### Login
\`POST /auth/login\`

### Logout
\`POST /auth/logout\`

### Current user
\`GET /auth/me\`

## Exams

### List exams
\`GET /exams\`

### Create exam
Admin only.

\`POST /exams\`

### Update exam
Admin only.

\`PUT /exams/{exam_id}\`

### Delete exam
Admin only.

\`DELETE /exams/{exam_id}\`

## Questions

### List questions
\`GET /exams/{exam_id}/questions\`

### Create question
Admin only.

\`POST /exams/{exam_id}/questions\`

### Update question
Admin only.

\`PUT /exams/{exam_id}/questions/{question_id}\`

### Delete question
Admin only.

\`DELETE /exams/{exam_id}/questions/{question_id}\`

## Attempts

### Start exam
Student only.

\`POST /exams/{exam_id}/start\`

### View attempt
\`GET /attempts/{attempt_id}\`

### Submit attempt
\`POST /attempts/{attempt_id}/submit\`

Example:
\`\`\`json
{
  "answers": [
    {"question_id": 1, "selected_option": "b"},
    {"question_id": 2, "selected_option": "a"}
  ]
}
\`\`\`

## Results

### Student results
\`GET /results\`

### Admin result list
Admin only.

\`GET /admin/results\`

### Admin analytics
Admin only.

\`GET /admin/analytics\`

## Health

\`GET /health\`

Returns HTTP 200 when the API can reach MySQL and HTTP 503 when the database is unavailable.
