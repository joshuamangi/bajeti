#!/bin/bash
LOGFILE="/var/log/ngrok-dns.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

log "Starting ngrok DNS updater..."

# Wait up to 30s for ngrok tunnel
for i in {1..30}; do
    NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[]? | select(.proto=="https") | .public_url')
    if [ -n "$NGROK_URL" ]; then
        log "Ngrok is ready: $NGROK_URL"

        # Retry AWS Route53 update up to 5 times
        for attempt in {1..5}; do
            log "Attempt $attempt: Updating Route53..."
            if /home/joshuamangi/projects/bajeti/scripts/update_ngrok_dns.sh >> "$LOGFILE" 2>&1; then
                log "Route53 update succeeded ✅"
                exit 0
            else
                log "Route53 update failed ❌, retrying in 5s..."
                sleep 5
            fi
        done

        log "Route53 update failed after 5 attempts ❌"
        exit 1
    fi
    log "Ngrok not ready yet... retry $i/30"
    sleep 2
done

log "Ngrok tunnel not found after 30s ❌"
exit 1
