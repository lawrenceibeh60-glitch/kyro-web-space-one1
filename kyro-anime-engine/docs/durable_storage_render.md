# KAE durable storage on Render (free-tier setup)

This guide configures KAE project documents to use managed PostgreSQL and uploaded audio to use an S3-compatible object store instead of relying on Render's ephemeral filesystem.

## What is durable, and what is not

- Project documents (scenes, drawings, layers, rigs, effects, timeline metadata) are stored in PostgreSQL when DATABASE_URL is set.
- Local development continues to use JSON files under KAE_PROJECTS_DIR when DATABASE_URL is absent.
- Uploaded audio bytes use S3-compatible object storage when all KAE_OBJECT_* variables are configured. Otherwise, audio is stored locally and is not durable on Render free services.
- Export job frames and output files remain temporary local files and may disappear after a restart or redeploy. Download finished exports promptly.
- Free database/object-store plans have provider-specific quotas, usage limits, retention rules, and backup limitations. Review the provider's current terms before trusting it with irreplaceable work.

## 1. Create a free PostgreSQL database

Neon is one possible provider; another PostgreSQL provider is fine if it gives you a standard PostgreSQL connection URL.

1. Create a database/project with the provider.
2. Copy its recommended PostgreSQL connection string.
3. Keep the connection string private. Never commit it to Git, paste it into an issue, or expose it in frontend JavaScript.
4. Use the provider's connection string and SSL requirements as given.

## 2. Configure Render project storage

In the Render dashboard, open the KAE web service, then Environment:

- Add DATABASE_URL with the PostgreSQL connection string.
- Keep KAE_MCP_API_KEY configured separately. Do not replace it with the database password.
- Save changes and let Render redeploy.

The app creates the required tables on first database use. First successful database initialization attempts a one-time import of readable local JSON projects from KAE_PROJECTS_DIR without overwriting rows already in PostgreSQL. On a fresh Render free instance, that directory may be empty because its filesystem is ephemeral.

## 3. Configure durable audio assets

Cloudflare R2 is one S3-compatible option. Create a private bucket and an API token with only the object read/write permissions KAE needs. Use the S3 API endpoint and credentials provided by the object-store provider.

Add these variables in Render Environment:

- KAE_OBJECT_ENDPOINT_URL — provider's S3-compatible API endpoint.
- KAE_OBJECT_BUCKET — private bucket name.
- KAE_OBJECT_ACCESS_KEY_ID — access key ID.
- KAE_OBJECT_SECRET_ACCESS_KEY — secret access key.
- KAE_OBJECT_REGION — optional; defaults to auto, unless your provider specifies another value.

These credentials stay server-side. Never place them in frontend code or commit them. If any required object-storage variable is missing, KAE deliberately falls back to local audio storage, which is not durable on Render free.

## 4. Verify persistence

After deployment, visit:

- /api/health — application process health.
- /api/health/storage — database and binary-asset durability status, without credentials or provider details.

A fully configured storage check should return HTTP 200 with projects_storage set to postgresql, projects_durable true, binary_assets_storage set to object-storage, and binary_assets_durable true.

Then:
1. Create a test project, add a drawing, save, refresh, and confirm it remains.
2. Upload a small audio clip, play it back, and confirm it downloads correctly.
3. Trigger a Render redeploy.
4. Confirm the project and audio still load.
5. Test audio deletion.
6. Delete the test project after verification.

Do not assume persistence works until these checks pass.

## 5. Backups and recovery

A database is not a backup by itself.

- Export important KAE projects as native project JSON and keep copies outside Render.
- Check database provider backup/export options and free-plan retention rules.
- Before storage migrations, export projects that cannot be replaced.
- Never run destructive database cleanup commands as a troubleshooting shortcut.

## 6. Temporary exports and future model assets

Export job frames and finished files are currently stored in local temporary directories and may disappear after a Render restart/redeploy. Download completed exports promptly. Durable model, texture, and video asset libraries should use object storage after their upload/download/delete flows have been integrated and tested.

## Troubleshooting

- Storage health reports filesystem for projects: DATABASE_URL is missing or blank on the deployed service.
- Storage health reports filesystem for assets: one or more KAE_OBJECT_* variables are missing.
- Storage health returns 503: check environment variable names, database/object-store availability, endpoint URL, credentials, and provider permissions. Responses deliberately avoid exposing secrets.
- No old projects appear: local files on Render may already have been lost before PostgreSQL was connected. Migration can only import files that still exist.
- Project JSON survives but export files do not: expected; exports remain temporary until a durable export-storage workflow is implemented.
