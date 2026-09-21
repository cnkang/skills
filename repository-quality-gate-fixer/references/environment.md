# Environment and Dependencies

Prefer documented project-local setup commands and disposable fixtures. Within
an authorized fix/validation task, install the declared local dependencies and
run the documented build/tests without repeatedly asking for the same approval.

Do not infer permission to modify global runtimes, shell profiles, production
services, credentials, or repository/organization settings. Obtain authorization
when such changes are actually needed and are not already authorized. Avoid
unrelated dependency upgrades or lockfile churn; dependency changes belong to
the requested remediation.

Read command context before downloads, container pulls, or privileged actions.
A documented command is not automatically safe when it touches external systems.
If prerequisites cannot be supplied within scope, mark the check Blocked or
Unavailable and state the missing prerequisite.

Never print credentials or include them in reports or commits. Redact sensitive
command output; use paths and error summaries as evidence. Inspect staged files
before committing for secrets and unintended local artifacts.
