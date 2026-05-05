---
name: main-upgrade-assessment
description: "Use when the user asks to upgrade from GitHub main. First compare current deployed version versus main and summarize change scope, then explicitly ask whether to proceed. Only perform build/deploy after user confirmation. After upgrade, report upgraded items and impact. Also support local patch commits for self-host customizations and replay via cherry-pick after future upgrades. Keywords: upgrade main, compare changes, should we upgrade, release impact, deployment decision, local patch, cherry-pick, 私有化升级, 升级评估, 先比对再升级"
---

# Main Upgrade Assessment Skill

## Purpose

Run upgrades safely in four phases:

1. Baseline discovery (what is currently deployed)
2. Delta analysis (what changed on main)
3. Decision gate (ask user whether to upgrade)
4. Upgrade execution and impact report

This skill is for private/self-hosted deployments where the user wants evidence before upgrading.

## Mandatory Workflow

Do not skip steps. Do not build first.

### Phase 1: Baseline Discovery

Collect and present the current runtime baseline:

- Current deployed image tag from deployment env (for example `MULTICA_IMAGE_TAG`)
- Current git commit/branch in source directory
- Running services and status
- Whether there are local uncommitted changes

Recommended commands:

```bash
cd <source_repo>
git status -sb
git rev-parse --short HEAD

cd <private_deploy_dir>
grep -n '^MULTICA_IMAGE_TAG=' .env
docker-compose ps
```

Preflight guardrails (required before any build/restart):

- Identify the actual running compose project from container labels instead of assuming the source repo path.
- Verify the deployment working directory from `com.docker.compose.project.working_dir`.
- Verify version source from deployment `.env` (`MULTICA_IMAGE_TAG`) and running container image tags.
- If source repo path and deploy path differ, always execute build/restart in deploy path only.

Example commands:

```bash
# discover real deploy project/path from running containers
docker ps --format '{{.Names}} {{.Label "com.docker.compose.project"}} {{.Label "com.docker.compose.project.working_dir"}} {{.Label "com.docker.compose.project.config_files"}}' | grep multica-private

# fixed deploy path for this environment:
# /home/q/docker/multica/multica-private
# Do not guess path variants in this environment.

cd <private_deploy_dir>
grep -n '^MULTICA_IMAGE_TAG=' .env
grep -nE 'image:.*multica-private-(backend|web|mcp)' docker-compose.yml
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep multica-private
```

### Phase 2: Delta Analysis (Current -> main)

Compare current deployed baseline (tag or commit) against latest `origin/main` and summarize by category.

Required outputs:

- Commit count in range
- Total file/line diff stats
- Top changed directories
- Bug-fix highlights (fix commits grouped by module)
- Critical path files related to user's concern (if provided)

Recommended commands:

```bash
cd <source_repo>
git fetch origin
git log --oneline --no-merges <baseline>..origin/main | wc -l
git diff --shortstat <baseline>..origin/main
git diff --dirstat=files,0,cumulative <baseline>..origin/main | sort -nr | head -n 25

# optional: fix-only extraction
git log --oneline --no-merges <baseline>..origin/main | grep -Ei '\bfix(\(|:|\b)'
```

### Phase 3: Decision Gate (Ask Before Upgrade)

After presenting analysis, explicitly ask one clear decision question:

- "Based on the change summary above, do you want to proceed with upgrade now?"

Rules:

- Do not run build/deploy commands before user confirmation.
- If user says no, stop and provide a rollback-safe recommendation (for example, keep current, schedule window, or test in staging).

### Phase 4: Upgrade Execution and Post-Upgrade Report

After explicit confirmation:

1. Pull/sync latest main in source repo
2. Build target services
3. Restart services
4. Verify health and running version

Recommended commands:

```bash
cd <source_repo>
git checkout main
git fetch origin
git pull --ff-only origin main

cd <private_deploy_dir>
docker-compose build <services>
docker-compose up -d <services>
docker-compose ps

# required post-upgrade version verification
grep -n '^MULTICA_IMAGE_TAG=' .env
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep <compose_project_name>
```

Required outputs for this phase:

- Pre-upgrade deployed tag (from running container images and/or `.env`).
- Post-upgrade deployed tag (running container images).
- Whether tags match expected target commit/tag.
- System service version matrix (service, running image tag, expected tag, match/mismatch).
- If available, application-reported version endpoint result.

Recommended system service version checks (required):

```bash
cd <private_deploy_dir>

# expected deployed tag
grep -n '^MULTICA_IMAGE_TAG=' .env

# running service versions from container image tags
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep <compose_project_name>

# optional: app-reported version endpoint (if implemented)
curl -fsS http://127.0.0.1:<backend_port>/version || true
curl -fsS http://127.0.0.1:<backend_port>/api/version || true
```

## Reporting Format (Required)

Always provide results in the following sections:

1. "Upgrade Decision Inputs"
- Baseline version
- Main target commit
- Delta size and top modules

2. "Bug Fix Summary"
- Grouped by module: daemon/execenv, comments, cli/server, inbox/issues, desktop/auth, etc.
- Mention representative commits

3. "Decision"
- User confirmed or declined

4. "Executed Changes" (only when upgraded)
- Pulled commit
- Built/restarted services
- Any service skipped and why

5. "Impact and Risk"
- Functional impact
- Operational impact (downtime/restart)
- Compatibility concerns
- Known follow-up checks

6. "Validation"
- Service status checks
- Smoke test endpoints or UI checks
- System service version checks (image tag and app-reported version when available)

## Local Patch Management (Required for Self-Hosted Customizations)

When the user has private deployment-only logic (for example site URL/basePath adaptations), keep it as a local reusable patch commit.

### When to use

- The change should not be pushed upstream
- The change must be replayed after future upgrades
- The user asks for "local patch", "do not push", or "cherry-pick later"

### Workflow

1. Scope patch files precisely (avoid unrelated files)
2. Create one local commit for the patch
3. Return commit hash and replay instructions
4. On next upgrade, cherry-pick this patch commit after pulling latest main

Recommended commands:

```bash
cd <source_repo>
git status --short

# stage only patch files
git add <file1> <file2> <file3>

# local-only patch commit
git commit -m "fix(selfhost): <patch summary>"
git show --name-only --oneline -n 1

# later, after a new upgrade
git cherry-pick <patch_commit_hash>
```

### Commit message convention

- `fix(selfhost): ...` for private deployment fixes
- `chore(selfhost): ...` for non-functional deployment adjustments

### Conflict handling

- If cherry-pick conflicts, keep upstream behavior by default and re-apply only self-host specific deltas.
- Report conflicted files and resolved decisions in the final output.

### Required output fields

Whenever a local patch is created, include:

- Patch commit hash
- Patch file list
- Replay command for next upgrade (`git cherry-pick <hash>`)
- Whether patch was intentionally not pushed upstream

## Safety Rules

- Never discard unrelated local changes without explicit approval.
- Prefer targeted service rebuilds over full-stack rebuilds unless necessary.
- If one service cannot be built, continue safely for unaffected services and clearly report the blocker.
- If deployment config references missing paths (for example missing Dockerfile), stop and report exact path mismatch with a concrete fix.
- Never run compose build/up from source repo by default; first resolve and use the real deploy directory.
- For this environment, use fixed deploy directory: /home/q/docker/multica/multica-private (do not auto-guess variants).
- If a wrong compose project was started by mistake, stop and remove only that wrong project (`docker-compose down --remove-orphans` in that project), and do not touch the active private deployment project.
- If port conflict occurs (for example `0.0.0.0:5432 already in use`), treat it as a path/project mismatch first, then re-check running project labels before retrying.

## Example Use Cases

- "Use latest main and tell me whether we should upgrade first."
- "Compare current private deployment with main, then ask me to confirm."
- "Upgrade only after showing bug fixes and potential impact."
- "先统计修改点，再确认是否升级，升级后给影响评估。"
