#!/bin/bash
set -e

# Retry up to 30s until ngrok API responds
for i in {1..30}; do
  NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[]? | select(.proto=="https") | .public_url')
  if [ -n "$NGROK_URL" ]; then
    echo "Ngrok is ready: $NGROK_URL"
    /home/joshuamangi/projects/bajeti/scripts/update_ngrok_dns.sh
    exit 0
  fi
  echo "Waiting for ngrok... ($i)"
  sleep 1
done

echo "Ngrok tunnel not found after 30s"
exit 1
