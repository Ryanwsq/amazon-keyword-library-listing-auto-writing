# Standalone repository bootstrap

- Status: local foundation complete
- Date: 2026-08-20
- Source type: approved sanitized project snapshot from the multi-project workspace
- Sharing: sanitized

## Included

- Project rules, status, end-to-end workflow and judgment boundaries.
- Project knowledge, decision history and sanitized handoffs.
- Eight existing draft Skill packages and their direct references.
- Standalone repository governance, validator, Git ignore rules and persistent task architecture.

## Excluded

- Raw chats, automatic memory trees and local terminal history.
- Product/competitor source files, ASIN/SKU run data, XLSX/CSV/ZIP/PNG artifacts and browser state.
- MCP keys, credentials, cookies, tokens, account details and external authorization state.
- Actual Codex task IDs, absolute paths and Worktree mappings; these remain in the ignored local thread map.

## Current task state

- The current Codex task is the logical `keyword-main` and has been titled `Amazon关键词词库｜主任务｜main`.
- The local repository has no remote and no commit yet.
- Existing eight Skills remain `draft`; no migration action is P1 evidence.
- The combined source-collection package and combined competition/trend package still require single-responsibility splitting, and a quality-validation package remains planned.
- Persistent side tasks must be created only after their target Skill packages exist and pass P0.

## Validation

- Standalone P0 validator: passed for 8 draft Skills and 63 repository files before this handoff was added.
- Local main task mapping: confirmed Git-ignored.
- Sensitive material: no raw business data or credentials were migrated.

## Next actions

1. Register the local repository as a Codex project and bind the current logical main task to it; the current app tooling cannot add a saved project or move the calling task itself.
2. Split source collection into SIF, Amazon autocomplete and SellerSprite Skills without changing confirmed business rules.
3. Split competition and trend, then create the independent quality-validation Skill.
4. Re-run P0 and inspect the full repository diff.
5. Create all persistent side tasks and record their local IDs only in the ignored thread map.
6. Create the private GitHub remote only after local review, repository ownership confirmation and explicit external-write approval.
