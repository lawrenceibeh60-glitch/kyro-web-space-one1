# PostgreSQL storage for KYRO Animation Engine

KAE uses PostgreSQL for durable project storage when `DATABASE_URL` is configured. Without it, the app keeps using atomic JSON files for local development and offline use.

## Configure a managed database

1. Create a PostgreSQL database with a provider that allows connections from your Render web service (Render PostgreSQL or another managed PostgreSQL provider).
2. Copy the provider's **internal/private connection URL** when the database and KAE service are in the same Render region and provider network. Otherwise use the provider's external connection URL and follow its network/TLS requirements.
3. In the KAE web service on Render, open **Environment** and add:
   - Key: `DATABASE_URL`
   - Value: the database connection URL copied from the provider
4. Save the environment change and allow Render to redeploy/restart KAE.
5. Open `/api/health`. The JSON response should include `"storage_backend":"postgresql"`. If it says `"filesystem"`, the environment variable is missing or blank.
6. Create a test project, refresh the page, and confirm it remains in the project list. Do not delete existing projects as a test.

## What KAE does automatically

- Creates the `kae_projects` table and its update-time index when PostgreSQL is first used.
- Stores each native .kae project document as JSONB, keyed by project ID.
- Imports readable legacy files at `<PROJECTS_DIR>/<project-id>/project.json` once per database, without overwriting an existing PostgreSQL row with the same ID.
- Records the one-time import in `kae_storage_migrations`.
- Uses PostgreSQL for project list, read, save, existence checks, and delete operations whenever `DATABASE_URL` is configured.
- Keeps filesystem storage as the local fallback when `DATABASE_URL` is absent.

## Important operational notes

- Keep `DATABASE_URL` private. Never put it in source code, frontend JavaScript, issue reports, or screenshots.
- A successful health response only confirms which storage backend is selected; it does not prove the database is reachable. The first database-backed request verifies connectivity.
- Back up the database using the provider's backup/export tools before schema or storage changes.
- If the KAE filesystem contains projects you need, configure PostgreSQL before the deployment loses that filesystem data. The importer can only copy files that still exist and are readable at the time the first database initialization runs.
- Do not switch between different production databases casually: each database has its own project collection and one-time filesystem-import marker.
