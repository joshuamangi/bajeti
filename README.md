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

[Requirements]
execute this command
pip freeze > requirements.txt\n

[Migrations]
Install alembic using pip install alembic
Configure the env.py file by importing the Base and the models and adding Base.metadata to the target_metadata

from data.db.db import Base  # import your Base
from data.db.models import models
target_metadata = Base.metadata

Edit the alembic.ini file with the sqlitedriver
sqlalchemy.url = sqlite:///data/db/data/bajeti.db

Generate the Migration Script
alembic revision --autogenerate -m "Add security_answer column to users"
alembic upgrade head

scp -r joshuamangi@192.168.1.120:~/projects/bajeti/data/db/data /Volumes/Stuff/Documents/Backup/sqlite

docker compose run --rm --entrypoint bash bajeti_app

how to do backups
mkdir -p recover_backup
cp -a app/templates recover_backup/templates_before_recover

working with ssh
ssh-keygen -t ed25519 -C "github-deploy@raspberrypi" -f ~/.ssh/id_rsa_github_deploy
copy to raspberry pi
cat ~/.ssh/id_rsa_github_deploy.pub | ssh joshuamangi@192.168.1.120 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
create PI_HOST,PI_KEY, PI_USER in Github

created backup with
aws s3api create-bucket \
  --bucket bajeti-db-backups \
  --region eu-west-2 \
  --create-bucket-configuration LocationConstraint=eu-west-2

db backup script is in
/home/joshuamangi/scripts/bajeti

backups are stored in
/home/joshuamangi/backups/db_backups/

check backups
aws s3 ls s3://my-bajeti-backups/
