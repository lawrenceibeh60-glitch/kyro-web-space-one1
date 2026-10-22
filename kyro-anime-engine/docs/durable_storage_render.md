# KAE durable storage on Render (free-tier setup)

This guide configures KAE project documents to use managed PostgreSQL rather than Render's ephemeral filesystem.

## What is durable, and what is not

- Project documents (scenes, drawings, layers, rigs, effects, timeline metadata) are stored in PostgreSQL when `DATABASE_URL` is set.
- Local development continues to use JSON files under `KAE_PROJECTS_DIR` when `DATABASE_URL` is absent.
- Uploaded audio bytes and export job files currently use the local filesystem. They are **not durable on Render's free web service**. Do not treat this project-document migration as durable binary-asset storage.
- Free database plans have provider-specific quotas, compute/sleep limits, retention rules, and backup limitations. Read the provider's current terms before relying on it for irreplaceable work.

## 1. Create a free PostgreSQL database

Neon is one possible provider; another PostgreSQL provider is fine if it gives you a standard PostgreSQL connection URL.

1. Create a database/project with the provider.
2. Copy its pooled or direct PostgreSQL connection string as recommended by that provider.
3. Keep the connection string private. Never commit it to Git, paste it into an issue, or expose it in frontend JavaScript.
4. Confirm the provider's SSL requirements. Use its provided connection string rather than constructing one manually.

## 2. Configure Render

In the Render dashboard, open the KAE web service, then **Environment**:

- Add `DATABASE_URL` with the PostgreSQL connection string.
- Keep `KAE_MCP_API_KEY` configured separately. Do not replace it with the database password.
- Save changes and let Render redeploy.

The app creates the required tables on first database use. The first successful database initialization also attempts a one-time import of any readable local JSON projects in `KAE_PROJECTS_DIR`, without overwriting rows already in PostgreSQL. On a fresh Render free instance, that directory may be empty because its filesystem is ephemeral.

## 3. Verify persistence

After deployment, visit:

- `/api/health` — application process health.
- `/api/health/storage` — database connectivity and storage mode. This endpoint does not return credentials or database host details.

The storage health endpoint should return HTTP 200 with `"storage":"postgresql"` and `"durable":true`. If it returns 503, inspect the Render deployment logs and the provider's connection settings; the response deliberately avoids exposing secrets.

Then create a small test project in KAE, save a drawing, refresh, and confirm the project is still present. After that, trigger a Render redeploy and repeat the check. Delete the test project when finished.

## 4. Backups and recovery

A database is not a backup by itself.

- Export important KAE projects as native project JSON and keep a copy outside the Render service.
- Check the database provider's backup/export options and free-plan retention rules.
- Before a schema or storage migration, export the projects you cannot afford to lose.
- Never run destructive database cleanup commands as a troubleshooting shortcut.

## 5. Binary assets (audio, renders, models)

KAE's current audio upload and export-job code writes binary files to local directories. On Render free web services those files may disappear on restart/redeploy, even when project JSON survives in PostgreSQL.

Durable binary storage needs an S3-compatible object store (for example, Cloudflare R2) plus private bucket credentials configured as server-side environment variables. That is a separate integration from `DATABASE_URL`; do not set fake credentials or claim audio/model assets are durable until upload, download, delete, and redeploy tests pass.

## Troubleshooting

- **Storage health returns `filesystem`:** `DATABASE_URL` is missing or blank on the deployed service.
- **Storage health returns 503:** check the private environment variable, database availability, SSL/connection URL, and provider network access.
- **No old projects appear:** local files on Render's free filesystem may already have been lost before PostgreSQL was connected. The migration can only import files that still exist.
- **Project JSON saves but audio is missing after redeploy:** expected until binary object storage is implemented and configured.
