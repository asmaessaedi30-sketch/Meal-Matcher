# Deploy Meal Matcher to Azure App Service

Meal Matcher is prepared for Azure App Service on Linux. The deployment uses:

- Python 3.13 and Gunicorn
- one Gunicorn worker because the current database is SQLite
- `/home/data` for the persistent database and server-side sessions
- `/health` for the App Service health check

## Prerequisites

1. An Azure subscription.
2. [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) installed.
3. A globally unique App Service name, for example `asma-meal-matcher`.

## Deploy

Run these commands from this `cs50x_final_project` directory:

```bash
az login
./deploy-azure.sh asma-meal-matcher meal-matcher-rg eastus
```

Replace `asma-meal-matcher` if that name is already taken. The script creates a
Basic B1 Linux App Service, deploys the project, enables persistent data storage,
sets a generated Flask secret, configures the health check, and restarts the app.

The included `meal_matcher/meal_matcher.db` is copied to persistent storage only
when `/home/data/meal_matcher.db` does not exist. Later code deployments therefore
do not overwrite production accounts or profiles.

## Configure secrets

In Azure Portal, open **App Services > your app > Settings > Environment
variables** and add:

| Name | Required | Value |
| --- | --- | --- |
| `GEMINI_API_KEY` | Yes for AI plans | Your Google Gemini API key |
| `MAIL_SERVER` | Yes for reset email | Usually `smtp.gmail.com` |
| `MAIL_PORT` | Yes for reset email | `587` |
| `MAIL_USERNAME` | Yes for reset email | SMTP login/email |
| `MAIL_PASSWORD` | Yes for reset email | SMTP app password |
| `MAIL_DEFAULT_SENDER` | Yes for reset email | Sender email |
| `MAIL_USE_TLS` | Yes for reset email | `true` |

`DATA_DIR` and `SECRET_KEY` are configured by the deployment script. Do not
upload `.env`.

After saving settings, restart the app and check:

```text
https://YOUR-APP-NAME.azurewebsites.net/health
```

The expected response is `{"status":"ok"}`.

## Logs and redeployment

Stream application logs:

```bash
az webapp log tail --name asma-meal-matcher --resource-group meal-matcher-rg
```

Redeploy code by running the same `deploy-azure.sh` command again. For production
growth or multiple App Service instances, migrate SQLite and filesystem sessions
to Azure Database for PostgreSQL and Redis before scaling out.
