# Universal Owner source preview

These features require an unreleased Runtime source checkout that you explicitly
select. Runtime 0.4.0 does not include these remote access and lifecycle features.
The release commit for MCP distribution 0.2.2 does not include them.
Skill 0.3.1 does not include them.

Do not use a source version string as proof of feature support. Before use,
confirm that the installed Runtime provides these commands:

- `remote-serve`
- `remote-mcp`
- `remote-event`
- `shared-device`

Do not automatically upgrade an existing destination. Do not automatically
migrate an existing destination. Do not automatically expose an existing
destination to remote access.

Immutable preview candidates (not accepted releases):

| Component | Source commit | Scope |
|---|---|---|
| Runtime | [`21623289efd508a9ded7db0e73974fb3ce7e1a9b`](https://github.com/cnkang/hermes-plugin-qdrant-memory/tree/21623289efd508a9ded7db0e73974fb3ce7e1a9b) | Provides `remote-serve`, `remote-mcp`, `remote-event`, `shared-device`, and Native Owner. This commit is a preview. |
| MCP adapter | [`4cc2f36048ae15460f0db339523d69e1a332e093`](https://github.com/cnkang/qdrant-memory-mcp/tree/4cc2f36048ae15460f0db339523d69e1a332e093) | Provides the Pi lifecycle extension and bridge configuration. This adapter requires the Runtime candidate in this table. |
| Hermes test host | [`8f5693af418256b89da17ddda18a9242f113dcf6`](https://github.com/NousResearch/hermes-agent/tree/8f5693af418256b89da17ddda18a9242f113dcf6) | Provides the Hermes test host. The adapter lockfile selects Pi SDK 1.3.0. |

Before installation, examine the selected commit, its review status, and its test
results. The commit identifiers let users select the same source code. They do
not indicate production approval.

Get user authorization before installation. Get user authorization before
credential changes. Get user authorization before destination changes. Get user
authorization before remote exposure.

One active Memory Owner controls the Runtime, authoritative Ledger, embeddings,
and Qdrant writes. Each local harness uses a separate grant through a loopback
bridge. Remote harnesses use Streamable HTTP at `https://<owner>/mcp`. They verify
the server certificate.

A host that supports only stdio uses the Runtime's `remote-mcp` bridge. This
bridge connects one MCP interface to another. The `/v1/tool` JSON endpoint
accepts only loopback connections.

SSH and VPN are optional. Users can select embedded Qdrant, self-hosted Qdrant,
or Qdrant Cloud.

This preview supports service credentials that an administrator provides in
advance. Each credential has high entropy and supports separate revocation.
The preview does not support OAuth, OIDC, or browser authorization.

Do not advertise OAuth MCP support. Always verify TLS certificates. Explicit
configuration can permit a private certificate authority.

Do not give an agent a database write key. Do not give an agent the Owner Ledger.
Do not give an agent a protected claim. Do not give an agent administrator
credentials.

The administrator binds the owner, logical agent, device, principal, space,
visibility, and permission. Each device of one logical agent uses separate
credentials, a separate principal, and a separate device ID. These devices share
the same private space and logical identity.

Each different agent uses a separate private space. Agents can share a project
space or shared space only with explicit authorization. Tool payloads cannot set
trusted identity.

After a denial, do not retry with another scope. Do not create a false logical
identity.

A new grant does not expose legacy private records or records without an agent
identity. New logical private grants use a separate v2 partition. Migration
requires explicit action and is outside this preview.

Operators use `shared-device validate`, `shared-device revoke`, and
`shared-device rotate`. This Skill does not authorize changes or token file
disclosure.

Revocation supports repeated requests. Rotation requires one active grant and
a new private output file. Rotation does not overwrite an existing file.

The Owner denies new requests if policy validation fails or the grant expires.
The Owner also denies new requests after revocation. The Ledger reconciles work
that the Owner already accepted durably.

The `remote-event` command supports the `--action status` and `--action cancel`
options. Each action applies only to capture receipts from the authenticated
device. The caller needs a current capture grant with write permission.

Get user authorization before cancellation. This Skill does not provide that
authorization.

Only raw input that has not entered preparation can enter the durable
`CANCELLED` state. The Ledger reconciles prepared, uncertain, and committed
writes. Cancellation does not clear a recovery gate. Cancellation does not
delete saved memories.

Pi treats `CANCELLED` as a terminal outbox result. This result does not indicate
a committed write.

Native Hermes Owner mode uses one MemoryProvider and the existing host Runtime,
worker, and LLM facade. Project capture requires an approved grant rule. It also
requires a separate profile list that explicitly permits project capture.

The additional shared reader cannot write data. Do not register a second MCP
memory interface in that Native profile.

A remote Hermes installation can use the explicit MCP fallback as its only
memory interface. Native mode does not support automatic operation as a remote
client.

The MCP repository provides the optional Pi lifecycle extension at
`integrations/pi/owner-memory.mjs`. The extension is off by default. It saves
only hook content that the grant permits.

The extension retains its pending events in the current authorized session.
The Owner performs extraction, duplicate detection, embedding, and persistence.

The temporary context hook refreshes authorized recall for each request. It does
not save shared recall in session history.

Pi 1.3.0 session tests and Hermes MemoryManager tests use deterministic models.
These tests do not establish accuracy with real models. They do not establish
user interface acceptance.

Codex, DSH, WorkBuddy, and OpenCode require explicit MCP use or assisted
operation. Automatic operation requires an official adapter and tests for that
agent. Skill instructions alone do not provide lifecycle hooks.

Read the [Runtime guide](https://github.com/cnkang/hermes-plugin-qdrant-memory/blob/21623289efd508a9ded7db0e73974fb3ce7e1a9b/docs/shared-memory/remote-owner.md)
for deployment, migration, rollback, and security details.

The dedicated service and Cloud Owner test examples remain previews. The Cloud
test does not run without credentials that grant the required access. Successful
availability tests do not establish that the Cloud test ran.

Small local LLM tests do not establish production extraction quality. The source
references identify a preview, not a production release.

Before installation, examine the review status. Confirm the required
dependencies.
