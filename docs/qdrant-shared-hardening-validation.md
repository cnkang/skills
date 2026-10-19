# Qdrant shared security guidance validation — 2026-10-19

Baseline main: `a3524b8ad3a2d66fb478e275531d929d1a345dc2`; initial clean local
branch HEAD: `4276afd5151fb335d4bbe53ab0be76d77e11635a`. Canonical Skill version
moves to 0.3.1 for this documentation update. Existing installer, source pins, lockfiles and published archives
remain unchanged.

The canonical Skill and shared, setup and maintenance references now document
Owner-only database write credentials, optional protected destination admission,
non-destructive diagnostic outcomes, coherent backups and unsupported remote
transport. Unpublished Runtime additions are explicitly distinguished from 0.4.0.
Agents are not instructed to install, enroll or change production settings implicitly.

Test-only fix `d054406a639c5e5f48d62ebb6e69a3fc14787e93` makes the exact-ID
authorization contract send valid delete arguments. Otherwise the current
Runtime's earlier input validator rejects an extra text field before reaching the
scope check that the test intends to exercise. The denial assertion is preserved.

Observed verification:

- `python scripts/validate_skills.py`: passed.
- The validate workflow's package and Python test command: 275 passed, 34 explicit
  optional runtime/host/installed-agent acceptance skips. Staging the new reference
  is required by the canonical Git-index packaging contract.
- Current Runtime plugin/shared contract with the explicit opt-ins enabled:
  26 passed.
- Real Hermes Skill paths and runtime E2E with the actual host and explicit
  opt-ins: 5 passed.
- Whitespace and public-content checks passed. No personal checkout paths,
  private deployment endpoints, credentials or task transcripts were added.

See the Runtime's [hardening report](https://github.com/cnkang/hermes-plugin-qdrant-memory/blob/main/docs/shared-memory/hardening-report.md)
after its PR merges for the implementation, self-hosted TLS/JWT isolation evidence,
residual risks and proposed bilingual release notes. Recommend Runtime 0.4.1 for
the compatible opt-in changes; authenticated cross-container transport belongs
to a separate 0.5.0 design. No Skill snapshot or other package was published.
