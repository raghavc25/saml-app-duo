#!/usr/bin/env bash
# Generates a self-signed cert/key pair the SP can optionally use to sign
# AuthnRequests / LogoutRequests. Not required for a basic Duo integration —
# only run this if you want the SP side signed too.
set -euo pipefail

cd "$(dirname "$0")/certs"

openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout sp.key -out sp.crt -days 3650 \
  -subj "/CN=saml-duo-app"

echo
echo "Generated certs/sp.key and certs/sp.crt"
echo "Set in your .env:"
echo "  SP_CERT_FILE=certs/sp.crt"
echo "  SP_KEY_FILE=certs/sp.key"
