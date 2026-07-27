#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "Usage: $0 <globally-unique-app-name> <resource-group> [location]"
  exit 2
fi

APP_NAME="$1"
RESOURCE_GROUP="$2"
LOCATION="${3:-eastus}"

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI is required: https://learn.microsoft.com/cli/azure/install-azure-cli"
  exit 1
fi

az account show >/dev/null 2>&1 || az login

if ! az group show --name "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az group create --name "$RESOURCE_GROUP" --location "$LOCATION" >/dev/null
fi

az webapp up \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --runtime "PYTHON:3.13" \
  --sku B1

SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"

az webapp config appsettings set \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --settings \
    SCM_DO_BUILD_DURING_DEPLOYMENT=1 \
    DATA_DIR=/home/data \
    SECRET_KEY="$SECRET_KEY" \
  >/dev/null

az webapp config set \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --startup-file "bash startup.sh" \
  --always-on true \
  >/dev/null

az webapp config set \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --generic-configurations '{"healthCheckPath":"/health"}' \
  >/dev/null

az webapp restart --name "$APP_NAME" --resource-group "$RESOURCE_GROUP"

echo
echo "Deployment finished: https://${APP_NAME}.azurewebsites.net"
echo "Add GEMINI_API_KEY and mail settings in Azure Portal > App Service > Environment variables."
