# Security

## Trust model

AI Delivery Analyst is a local, single-user service. It binds only to an explicit loopback address. Other operating-system users are considered untrusted and must not be able to read the application's `.env`, database, browser session, or process environment. Processes running under the same OS account are trusted; stronger isolation requires a separate OS account or container boundary.

The service is not designed for direct Internet or LAN exposure. A reverse proxy does not turn the current access-token flow into multi-user authentication.

## Secrets and sessions

- Store `ADA_ACCESS_TOKEN`, Jira/Trello credentials, and optional integration tokens only in the ignored `.env` file with mode `0600`.
- Browser requests contain only a profile ID. Source credentials, JQL, and board IDs remain in server memory.
- Login exchanges `ADA_ACCESS_TOKEN` for an in-memory, `HttpOnly`, `SameSite=Strict` session cookie. Sessions expire after eight hours and are lost on restart.
- Never put credentials in URLs, source control, logs, screenshots, documentation, or issue attachments.
- Rotate a credential immediately if it has been exposed. Rotation is an operator action and is not performed automatically by the application.

## Network and ingestion controls

- `HOST` must be loopback.
- CORS origins are allowlisted. Jira destinations must be HTTPS Atlassian Cloud origins or explicit `ADA_ALLOWED_JIRA_HOSTS` entries.
- JSON request bodies require `application/json`, `Content-Length`, a complete JSON object, and are limited to 64 KiB with a read timeout.
- HTTP and scheduled syncs share a bounded queue. Jira/Trello item limits and ingestion deadlines fail closed: no partial snapshot is saved.

## Reporting

Report suspected vulnerabilities privately to the repository owner. Include the affected revision, reproduction steps, and impact. Do not include live credentials or customer data in the report.
