# Ownership, recovery and scoped deletion

For `writer_busy`, locate the active session/gateway and coordinate stopping it;
wait for workers and in-flight requests to release ownership. Never remove its
lock. Stop writers on other machines and profiles too. Embedded storage also
rejects concurrent read clients while a provider holds its file lock.

PENDING operations recover on provider startup. FAILED work requires correcting
the underlying problem and explicit retry authorization. `hermes qdrant-memory
retry` can commit prepared operations, but only requeues raw events for later
trusted provider extraction. SUPERSEDED migration work is terminal, not proof of
successful import or permission to restore later-deleted records.

For a new scoped deletion:

1. Confirm authorization, exact active profile, destination, collection, user
   and agent. Omit agent only when the no-agent scope is intended.
2. Coordinate exclusive access and run the preview:
   `hermes qdrant-memory delete-all --user USER --agent AGENT --dry-run`.
3. Show `would_delete`, `scopes`, `scope`, `collection`, `resumed` and relevant
   backlog limitations. Counts of existing points do not enumerate every pending
   event/write that execution fences. Do not widen the scope to all agents.
4. Only with explicit authorization covering that deletion execute the same
   scope with `--confirm`. Never silently confirm from a diagnostic request.
5. Require success and verify before restarting writers.

If `scope_delete_recovery_required` or `scope_delete_incomplete` appears, preserve
the ledger and resume the recorded scope through `delete-all --confirm` under
the original authorization. Do not change scope, clear the collection or bypass
recovery. A legacy ambiguous intent requires operator disambiguation using
`--resolve-legacy single_agent|all_agents`; it is incompatible with dry-run and
requires explicit confirmation. Stop for user choice if that intent is unclear.

For `reset_recovery_required`, the plugin requires `init` with the same destination
to finish an already authorized collection reset. Explain that this resumes a
destructive intent; confirm its authorization before doing so. New `init
--existing clear` is collection-wide destruction and is outside ordinary scoped
deletion. Never select it to fix a diagnostic failure.

Do not expose secrets, private service response bodies or unnecessary memory
text when diagnosing errors. Check nonzero exits and structured error codes;
a dry-run proves neither target readiness nor ability to acquire a future lease.
