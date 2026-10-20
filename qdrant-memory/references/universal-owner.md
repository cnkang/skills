# Universal Owner source preview

These features require an explicitly selected unreleased Runtime checkout. Runtime 0.4.0,
MCP distribution 0.2.2's release pin, and Skill 0.3.1 do not include the new
remote/lifecycle implementation. Do not treat a source version string as proof.
Discover `remote-serve`, `remote-mcp`, `remote-event` and `shared-device` before
using these instructions. Do not upgrade, migrate or expose an existing user
destination automatically.

Immutable preview candidates (not accepted releases):

| Component | Source commit | Scope |
|---|---|---|
| Runtime | [`d13b72c1bef47bcc6b261333f38b8916bafaed1e`](https://github.com/cnkang/hermes-plugin-qdrant-memory/tree/d13b72c1bef47bcc6b261333f38b8916bafaed1e) | `remote-serve`, `remote-mcp`, `remote-event`, `shared-device`, and Native Owner; PR 69 is held pending review and CI. |
| MCP adapter | [`8b206568210219674e8ea45ce606c8c3572afa57`](https://github.com/cnkang/qdrant-memory-mcp/tree/8b206568210219674e8ea45ce606c8c3572afa57) | Pi lifecycle extension and preview bridge configuration, including reviewed UTF-8, single-flight and credential binding fixes; requires the Runtime candidate above. |
| Hermes acceptance host | [`8f5693af418256b89da17ddda18a9242f113dcf6`](https://github.com/NousResearch/hermes-agent/tree/8f5693af418256b89da17ddda18a9242f113dcf6) | Host used by the source-preview acceptance lane; Pi SDK 1.3.0 is fixed in the adapter lockfile. |

Verify the selected commit and its review/check status before installation. These
identifiers make the preview reproducible; they do not confer production approval
or authorize installation, credential changes, destination changes or exposure.

One active Memory Owner owns the Runtime, authoritative Ledger, embeddings and
Qdrant writes. Multiple local Harnesses use independent loopback bridge grants;
remote Harnesses use verified `https://<owner>/mcp` Streamable HTTP. A stdio-only
Host uses the Runtime's `remote-mcp` MCP-to-MCP bridge. The old `/v1/tool` JSON
endpoint remains loopback-only. SSH, VPN and Qdrant Cloud are not prerequisites.
Embedded, self-hosted Qdrant and Cloud remain independent storage choices.

This preview supports pre-provisioned, high-entropy, independently revocable
service credentials. It does not implement OAuth/OIDC or browser authorization.
Never advertise OAuth MCP interoperability. TLS verification is mandatory; a
private CA may be explicitly trusted. Never give an Agent a database write key,
Owner Ledger, protected claim or administrator credential.

The administrator binds owner, logical agent, device, principal, space,
visibility and permission. Two devices of one logical agent use different
credentials/principals/device IDs bound to the same private space and logical
identity. A different agent uses its own private space, and may share only an
explicitly authorized project/shared space. Tool payloads cannot set trusted
identity. A denial does not permit retrying under another scope or fabricating
a logical identity. Legacy private/null-agent records are never exposed by a
new grant. New logical private grants occupy their own v2 partition; migration
is explicit and outside this preview.

`shared-device validate/revoke/rotate` is an operator interface. Loading this
Skill grants no permission to invoke mutation commands or disclose token files.
Revoke is repeatable. Rotation accepts one active grant and a new private output
file; it refuses overwrite. Live policy failure/revocation/expiry denies new
requests. Already durably accepted work finishes by Ledger reconciliation.

In the source preview, `remote-event --action status|cancel` can inspect/control
only the authenticated device's own capture receipts. A caller needs a writable,
currently authorized capture grant. Cancellation is a mutation and needs the
user's authorization; this Skill does not grant it. Only raw unprepared input
may become durably `CANCELLED`; prepared, uncertain and committed writes must
reconcile. Cancellation does not clear a recovery gate or delete saved memories.
Pi treats `CANCELLED` as a distinct terminal outbox result, never a committed write.

The Native Hermes Owner mode retains one MemoryProvider and one existing host
Runtime, worker and LLM facade. Explicit project capture additionally requires
an approved rule in the grant and a separate profile opt-in list. The additive
shared reader is read-only. Do not register a second MCP memory interface in
that Native profile. Remote Hermes installations may use the explicit MCP
fallback as their one memory interface; Native remote-client automatic mode is
not implemented.

Pi has an optional actual lifecycle extension in the MCP repository's
`integrations/pi/owner-memory.mjs`. It defaults off, saves only permitted hook
content, retains its own pending events in the current authorized session, and
uses the Owner for extraction/dedupe/embedding/persistence. Its ephemeral context
hook refreshes authorized recall for each request and does not persist shared
recall in history. Actual Pi 1.3.0 session and actual Hermes MemoryManager tests
use deterministic models; they do not prove real model accuracy or user UI
acceptance. Codex, DSH, WorkBuddy and OpenCode remain explicit MCP/assisted until
their own official automatic adapters are implemented and tested. Skill text
alone never provides a lifecycle hook.

Source deployment, migration/rollback and security details:
[Runtime guide](https://github.com/cnkang/hermes-plugin-qdrant-memory/blob/d13b72c1bef47bcc6b261333f38b8916bafaed1e/docs/shared-memory/remote-owner.md).
The dedicated service and Cloud Owner test examples also remain previews.
Missing scoped Cloud credentials skip that credentialed job; successful
availability checks are not evidence of Cloud execution. Small local LLM
diagnostics, even when passing, are not production extraction-quality guarantees.
The immutable references denote a preview, not an accepted production release.
Recheck review status and required dependencies before installation.
