# bajeti

Dockerfile, which contains the layers required when creating the container image
docker compose file contains the application configurations

## Deployment to raspberry pi

git add .
git commit -m “”
git push -u origin

Go into raspberry pi

cd [to project folder]
git clone [git path]
cd bajeti
add .env fiel
docker compose up -d —build —remove-orphans
docker  logs -f bajeti_app
