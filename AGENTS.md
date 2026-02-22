# Role and Goal
You are an expert Python developer and M365/Azure Cloud Architect.

Build and maintain a Python UTCM exporter that:
- Authenticates to Microsoft Graph.
- Creates UTCM snapshots with a resource list.
- Polls asynchronous job completion.
- Downloads snapshot JSON.
- Splits resources into deterministic YAML files for Git historization.

# API Context (2026 UTCM Beta)
Use Microsoft Graph beta UTCM Snapshot APIs.

1. Start snapshot job  
`POST https://graph.microsoft.com/beta/admin/configurationManagement/configurationSnapshots/createSnapshot`

2. Poll job status  
`GET https://graph.microsoft.com/beta/admin/configurationManagement/configurationSnapshotJobs/{jobId}`

3. Download result  
Read `resourceLocation` from completed job and `GET` snapshot JSON.

Accepted terminal statuses in this project:
- `succeeded`
- `partiallySuccessful`

# Resource Source of Truth
Do not use `utcm-monitor.json` as the only source for runnable resource lists.

Generate `resources.json` from official UTCM docs pages via:
- `scripts/build_resources_catalog.py`
- `src/utcm_exporter/resources_catalog.py`

Rationale:
- Schema can contain entries not currently accepted by `createSnapshot`.
- Docs are closer to currently supported public set.

Runtime behavior:
- If Graph returns `400` with `"ResourceType '...' is not supported."`, the client removes those resource IDs and retries automatically.

# Required Directory Structure
Persist parsed files in:
`./tenant_state/{workload}/{resource_type}/{resource_display_name_or_id}.yaml`

Examples:
- `tenant_state/entra/conditionalaccesspolicy/Require_MFA_For_Admins.yaml`
- `tenant_state/exchange/transportrule/Block_External_Forwarding.yaml`

# Rules for the Scripts
1. Use `msal` client credentials flow with `.env` values:
`AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`.
2. Use `requests` for HTTP calls.
3. Use `uv` for dependency/project management.
4. Use Python `logging` for progress.
5. Sanitize filenames by removing invalid characters: `\ / : * ? " < > |`.
6. YAML output must be deterministic:
- block style
- stable key ordering (`sort_keys=True`)
- consistent indentation (`indent=2`)
7. Parser naming precedence:
- instance `displayName` / `name` / `id`
- fallback to top-level resource `displayName` (for shapes like Teams meeting policy)
- fallback default `item_NNN`
8. Teams meeting policy naming normalization:
- if top-level `displayName` is `Prefix-Name`, use `Name`.
9. Pruning:
- remove stale `.yaml` files not present in current snapshot when clean mode is enabled.
- remove empty directories after prune.

# Current Scripts
- `scripts/test_graph_connectivity.py`: verifies Graph auth by calling `/v1.0/organization`.
- `scripts/build_resources_catalog.py`: builds `resources.json` from docs pages.
- `scripts/run_utcm_snapshot.py`: runs snapshot using `resources.json` by default; supports `--resources` override.
- `scripts/parse_snapshot.py`: downloads/parses snapshot into YAML, supports `--debug` dump and clean/no-clean modes.
- `scripts/cleanup_snapshot_jobs.py`: deletes old UTCM snapshot jobs by status/age.

# Known Operational Notes
- Snapshot `displayName` must be 8-32 chars and only letters/numbers/spaces.
- Snapshot jobs are created with unique names by default.
- Full exports can run for many minutes; use larger timeout values when needed.
- `partiallySuccessful` means some requested resources were not returned; compare requested vs snapshot `resources`.

# Not Implemented Yet
Step 4 (automatic Git add/diff/commit orchestration) is intentionally deferred for later.
