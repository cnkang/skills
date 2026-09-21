# Kiro Setup

The package includes `.kiro/agents/conventional-commit-batcher.json`, its prompt, a short steering file, and an optional scope-check hook. The hook is an agent prompt, not a deterministic shell security boundary.

Keep the complete package together. The root [SKILL.md](../SKILL.md) is the
canonical entrypoint; adapters only route to it. If copying adapters into a
different project location, update their relative pointers to the installed
package and keep both validator and safety-gate scripts available. Do not copy
only `core-rules.md`: it links to other package resources.

The workflow applies to mixed changes needing separate commits. It does not
intercept every Git operation, and it does not grant authorization. To request
execution, ask to split and commit the relevant changes. To request only a plan,
say so explicitly. Pushing remains a separate requested action.

Use the target host's supported installation mechanism; verify discovery there.
These adapters are not proof of compatibility with every host version. When
updating, synchronize the installed copy with the package and check for local
customizations first.
