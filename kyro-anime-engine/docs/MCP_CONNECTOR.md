# KAE universal AI connector (MCP)

KAE exposes native project editing tools through a provider-neutral Model Context Protocol (MCP) endpoint. Any AI client that supports remote MCP and bearer-token authentication can potentially connect; each provider has its own registration rules and feature limits.

## Endpoint

- URL: https://YOUR-KAE-HOST/mcp (local example: http://127.0.0.1:5000/mcp)
- Transport: JSON-RPC 2.0 over HTTP POST
- Authentication: Authorization: Bearer KAE_MCP_API_KEY
- Protocol: MCP Streamable HTTP, currently advertising protocol version 2025-11-25
- Extra Python dependencies: none

## Enable it

1. Generate a long, random secret and set it as the KAE_MCP_API_KEY environment variable on the KAE server.
2. Restart KAE. If the secret is missing, /mcp returns HTTP 503 and does not expose tools.
3. Keep the secret private. Never put it in frontend JavaScript, checked-in files, screenshots, or prompts.
4. Connect a compatible MCP client to the endpoint with bearer-token authentication. Use HTTPS for remote connections. For local-only KAE, use the client's supported local transport or a secure tunnel rather than exposing an unauthenticated port.

## Tools

- kae_list_projects: find available projects and IDs.
- kae_create_project: create a native KAE project when the workspace is empty or the user requests a new project.
- kae_get_project: inspect the canonical KAE project document.
- kae_get_scene_context: inspect a scene, layer order, exposures and drawing catalog.
- kae_add_drawing: add validated native vector artwork.
- kae_append_strokes: append editable strokes to an existing drawing.
- kae_create_drawing_layer: place a drawing on the scene timeline.
- kae_update_layer: update name, visibility, lock state, opacity or transform.
- kae_delete_layer: remove a layer only when confirm=true is supplied.

## Recommended AI workflow

1. Call kae_list_projects and identify the user's intended project. If none exists and the user wants a new one, call kae_create_project.
2. Call kae_get_project and kae_get_scene_context before editing.
3. Read canvas dimensions from project settings and author strokes in those coordinates.
4. Add artwork with kae_add_drawing, then expose it on the timeline with kae_create_drawing_layer.
5. Re-read the scene to verify that changes were saved.

## Security and current limitations

- Every MCP request requires the configured bearer secret.
- Layer deletion requires explicit confirmation.
- Every write validates the complete native project before saving.
- The connector is stateless on the MCP transport. The editor polls its project revision every 1.5 seconds and loads saved AI edits when there are no unsaved local edits. If the local document is dirty, KAE warns rather than silently overwriting the user's changes.
- Generic MCP support does not guarantee every AI provider permits custom server registration. The connector is provider-neutral; client-side availability depends on each provider and account.
