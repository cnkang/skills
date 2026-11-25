# Search policy

Use this reference to decide when a memory search is worth doing and how to
phrase it. Do not search on every turn. Do not skip a search only because the
user did not say "remember".

## Consider a search

Consider a scoped search when the task builds on earlier work:

- Continuing or resuming a project.
- Investigating a problem that may have occurred before.
- Preparing a release, a migration or a maintenance window.
- Reviewing an earlier architectural decision.
- Applying established user preferences to a new deliverable.
- Revising or correcting an implementation that memory may describe.
- Planning work that depends on a previous decision.
- Running a workflow that the user repeats.

## Do not search by default

- A translation, a calculation or a stateless factual question.
- A task that is unrelated to preserved context.
- A task whose inputs are already complete in the conversation or the repository.
- A repeat of an identical search with no new information need.

## Workflow

1. Identify the intent of the task.
2. Decide whether historical memory could change the result.
3. Identify the authorized scope.
4. Build focused queries.
5. Retrieve only what the task needs.
6. Validate each result against current evidence.
7. Apply the useful part.
8. Search again only if a material gap remains.

One or two well-formed queries are usually enough. Do not run a search loop. Do
not add an extra model call that only decides whether to search.

## Query construction

A useful query names its subject and keeps the terms that identify the record.

- Keep project names, component names, technologies, versions and identifiers.
- Keep one retrieval intent for each query.
- Remove conversational context that adds no identifying term.
- Split a complex question into separate searches when the parts have different
  subjects.
- Keep the query to the identifying terms. A query is not a transcript, so leave
  long documents out of the embedding input.

| Poor query | Better query |
|---|---|
| `What did we do before?` | `Qdrant Memory Runtime embedding fingerprint upgrade compatibility decisions` |
| `Release requirements` | `Runtime release validation and packaging requirements` |
| `Release requirements` | `MCP distribution exact Runtime dependency compatibility` |
| `Release requirements` | `Hermes Plugin Catalog immutable version pin requirements` |
| `editor` | `preferred editor for Project Cedar` |

A query that needs several unrelated subjects is several queries. Keep each one
short and specific. Prefer the noun phrase that the memory itself would use.

## Multilingual queries

Memory text keeps the language that it was written in. A query in another
language can still match by meaning, but exact terms help.

- Write the query in the language that the memory probably used, when you know it.
- Keep identifiers, paths, commands and version strings exactly as written. Do
  not translate them.
- For mixed Chinese and English work, put the English technical term and the
  Chinese subject in one query.
- Do not assume that a translated query is equivalent. If the first query
  returns nothing material, try one bounded rewrite with the key term from the
  other language.

## Apply results

- Read the payload fields that you need: `text`, `source`, `session_id`,
  `created_at`, `updated_at`, `category` and `metadata`.
- Check each result against the repository, the installed version or the current
  configuration before you act on it.
- Keep provenance out of user-facing text unless the user needs it.
- Do not report a search result as a verified fact.

## Report memory impact

When a remembered fact materially changed the result, one short clause in the
normal reply is enough. The reply must remain complete without that clause.

Report it when:

- A remembered constraint changed the design or the verification steps.
- A remembered procedure added a check that the task would otherwise have missed.
- A remembered failure cause prevented a repeated mistake.

Do not report it when:

- The search returned nothing useful, or you did not act on the result.
- The memory is unrelated, stale or already rejected.
- You wrote the memory earlier in the same turn.
- The memory only confirmed what the current context already showed.

Rules:

- Do not name the memory system and do not quote stored text.
- Do not add a heading, a section or a fixed phrase.
- Do not claim memory use that did not happen.
- Do not describe a search result as proof that memory helped.
- Keep private details out of the explanation.

Examples:

- "The earlier compatibility constraint is why this change keeps the old read
  path and adds a regression test."
- "按此前记录的发布流程，本次额外核对了依赖版本、打包结果和回退路径。"
- Avoid: "I searched memory and found three relevant records."
- Avoid: "Based on my long-term memory, the project uses SQLite." — a fixed
  phrase that reports a search rather than a result.

The memory system should be useful without being intrusive. Use it naturally and
keep the report short.
