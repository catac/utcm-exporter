# Role and Goal
You are an expert Python developer and M365/Azure Cloud Architect. Your goal is to write a Python application that authenticates to Microsoft Graph, triggers a Unified Tenant Configuration Management (UTCM) snapshot, downloads the result, and unpacks the tenant configuration into a structured local Git repository for version tracking.

# API Context (Critical: 2026 UTCM Beta API)
You will use the Microsoft Graph beta UTCM Snapshot APIs. These run asynchronously.
1. **Start Snapshot Job**: `POST https://graph.microsoft.com/beta/admin/configurationManagement/configurationSnapshots/createSnapshot`
   - Request Body: `{"displayName": "GitBackup", "description": "Automated Backup", "resources": ["microsoft.entra.conditionalaccesspolicy", "microsoft.exchange.transportrule", "microsoft.teams.meetingpolicy"]}`
2. **Poll Job Status**: `GET https://graph.microsoft.com/beta/admin/configurationManagement/configurationSnapshotJobs/{jobId}`
   - Extract the `{jobId}` from the POST response.
   - Poll every 10-15 seconds. The `status` field will progress through `notStarted`, `running`, `succeeded`.
3. **Download Result**: Once `status` is `succeeded`, extract the `resourceLocation` property (a URL) and HTTP GET it to download the JSON snapshot.

# Resources JSON Schema
Check the available resources to export and the existing fields in the json schema defined here: https://www.schemastore.org/utcm-monitor.json

# Required Directory Structure
When the snapshot JSON is downloaded, parse it and split the resources into the local file system using this structure:
`./tenant_state/{Workload}/{ResourceType}/{ResourceDisplayName_or_ID}.json`

*Example:*
- `tenant_state/entra/conditionalaccesspolicy/Require_MFA_For_Admins.json`
- `tenant_state/exchange/transportrule/Block_External_Forwarding.json`

# Rules for the Script
1. Use `msal` for Client Credentials Flow authentication (App ID, Tenant ID, Client Secret via `.env`).
2. Use `requests` for HTTP calls.
3. Sanitize file names (remove invalid characters like `\`, `/`, `:`, `*`, `?`, `"`, `<`, `>`, `|`).
4. Format all saved JSON files with an indent of 2 spaces and sort keys to ensure consistent Git diffs.
5. If a resource lacks a `displayName` or `name`, fallback to its `id` for the filename.
6. Use Python `logging` to output progress (do not use basic `print`).
