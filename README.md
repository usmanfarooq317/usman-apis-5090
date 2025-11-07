# usman-apis-5090

Single-file Flask app demo (frontend + backend on same port 5090).
Image name: usman-apis-dashboard
DockerHub user: usmanfarooq317

## Run locally
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export PORT=5090
python app.py
# App available at http://localhost:5090

## Docker
docker build -t usmanfarooq317/usman-apis-dashboard:latest .
docker run -d --name usman-apis-dashboard -p 5090:5090 usmanfarooq317/usman-apis-dashboard:latest

## Jenkins
- Create Credentials:
  - `docker-hub` (Username/Password for Docker Hub)
  - `usman-ec2-key` (SSH private key for EC2 user)
- Create pipeline job with Jenkinsfile or import `jenkins-job.xml`.
- Ensure Jenkins agents have docker and `jq` installed (or adapt Jenkinsfile).

## Endpoints
- GET /           -> single-page frontend
- GET /api/version
- GET /api/health
- GET /api/metrics
- POST /api/auth/login {username,password} -> returns JWT token
- GET /api/secure (Authorization: Bearer <token>)
- GET/POST/PUT/DELETE /api/items

