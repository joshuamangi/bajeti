#!/bin/bash

# Config
HOSTED_ZONE_ID="ZET8N8SCGHUU0"
RECORD_NAME="bajeti.techjamaa.com."

# Get the current ngrok public URL (https one)
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[] | select(.proto=="https") | .public_url')

if [ -z "$NGROK_URL" ]; then
  echo "No ngrok tunnel found"
  exit 1
fi

# Extract the hostname only (remove https://)
TARGET=$(echo $NGROK_URL | sed 's#https://##')

# Create Route53 change batch JSON
cat > change-batch.json <<EOF
{
  "Comment": "Update bajeti subdomain to ngrok",
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "$RECORD_NAME",
        "Type": "CNAME",
        "TTL": 60,
        "ResourceRecords": [{ "Value": "$TARGET" }]
      }
    }
  ]
}
EOF

# Update Route53
aws route53 change-resource-record-sets --hosted-zone-id $HOSTED_ZONE_ID --change-batch file://change-batch.json
