# C / NGINX Checks

Use the repository's NGINX development guide and harness contracts when relevant.
Review changed code for request lifecycle, filter order/return semantics, pool
ownership, buffer/chain lifetime, cleanup, directive parsing and config merging.

For affected paths, consider streaming/buffering, subrequests, aborted requests,
and supported NGINX versions. Prefer the project's integration harness; a unit
test does not alone prove the live filter path is reached.

Use existing debug/sanitizer tooling for memory-safety-sensitive changes where
available. Respect documented shared build-directory constraints when scheduling
checks. Missing NGINX binaries or module artifacts leave native gates unverified.

Do not modify system NGINX or run privileged/production tests without the needed
authorization. Prefer project-local builds and disposable test configurations.
