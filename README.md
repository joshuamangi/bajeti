# bajeti

## All this is running in techjamaa00

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
docker  logs -f bajeti_app [to check if the service is running and the logs]

created an ngrok service to start the service upon restart using
sudo nano /etc/systemd/system/ngrok.service

[Unit]
Description=ngrok tunnel for FastAPI app
After=network.target

[Service]
User=joshuamangi
WorkingDirectory=/home/joshuamangi
ExecStart=/usr/local/bin/ngrok http 8000 --log=stdout
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

ngrok config add-authtoken <your-ngrok-auth-token>

execute these commands after
sudo systemctl daemon-reload
sudo systemctl enable ngrok
sudo systemctl start ngrok

check if service is running sudo systemctl status ngrok
