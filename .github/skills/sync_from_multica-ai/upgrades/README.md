# Upstream Upgrade Archive

This directory tracks upgrades from `multica-ai/multica` into the local fork.

Each upgrade record should contain:

- Source, target, baseline, upstream, and merge commits
- Ahead/behind counts and change-size metrics
- User-visible features and operational changes
- Database migration range and destructive operations
- Local customization compatibility checks
- Configuration gaps and rollout risks
- Validation, push, build, deployment, and rollback status
- Follow-up actions with checkboxes

## Records

| Date | Target | Upstream | Merge | Risk | Status | Record |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-08-23 | `qaihub_multica` | `0716081bb` | `7446e2f35` | High | Merged locally; push and deployment pending | [2026-08-23-upstream-main-0716081bb.md](2026-08-23-upstream-main-0716081bb.md) |
