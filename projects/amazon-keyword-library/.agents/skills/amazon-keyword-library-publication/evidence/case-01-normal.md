# Case 01 — sanitized evidence publication

- Case type: `normal`
- Registry status: `candidate`
- Sanitized case reference: `gaming-chair-evidence-publication-01`
- Execution environment: existing private project repository
- Locked Git revision of source Run: `4a903057765e136c85c5dc4704178c076f3ce467`
- Acceptance: `pending user review of this publication batch`

## Input classification

- Imported: module-level aggregate counts, capability IDs, locked revision, quality conclusions and user-confirmed status boundaries.
- Local-only evidence: original workbooks, screenshots, raw exports, manifests, logs and local Run directories.
- Excluded: credentials, account sessions, absolute paths, Codex task IDs, brands, ASINs and verbatim product input.
- Needs decision: whether this publication case itself is accepted after the user reviews the tracked diff.

## Capability actually exercised

- `keyword.library.publish`

## Output

本批为实际执行的模块创建独立脱敏案例文件，更新十二个证据索引、历史案例摘要、知识索引、项目状态、版本决策和端到端同步说明。业务规则、阈值、能力状态和Skill maturity均未改变。

## Quality checks

要求仓库结构验证、差异检查和敏感信息扫描通过后才保留为候选。commit、push和外部发布不在本次授权内。

## Conclusion

本案例当前为`candidate`。用户确认本批发布结果后才能改为`accepted`；在此之前不构成publication Skill的P1案例。
