---
name: main-upgrade-assessment
description: "Use when the user asks to upgrade from GitHub main. First compare current deployed version versus main and summarize change scope, then explicitly ask whether to proceed. Only perform build/deploy after user confirmation. After upgrade, report upgraded items and impact. Support local branch workflow (qaihub_multica) for archiving local customizations and merging/rebasing upstream main changes. Keywords: upgrade main, compare changes, should we upgrade, release impact, deployment decision, local branch, merge, rebase, 私有化升级, 升级评估, 先比对再升级, 本地分支"
---

# Main Upgrade Assessment Skill

## Purpose

Run upgrades safely in four phases with support for local branch workflow:

1. Baseline discovery (what is currently deployed, current branch state)
2. Delta analysis (what changed on main relative to local branch)
3. Decision gate (ask user: upgrade strategy + proceed?)
4. Upgrade execution and impact report

Before asking for confirmation, the AI must provide an explicit recommendation:
- Recommend: Upgrade now / Defer upgrade
- Explain why (benefits, risks, urgency)
- Include confidence level (High/Medium/Low)

This skill supports:
- Private/self-hosted deployments
- Local branch archiving (`qaihub_multica`)
- Two upgrade strategies: **merge** (preserve commit history) or **rebase** (linear history)

## Mandatory Workflow

Do not skip steps. Do not build first.

### Phase 1: Baseline Discovery

Collect and present the current runtime baseline:

- **Git state**: Current branch, HEAD commit, local changes, unpushed commits
- Current deployed image tag from deployment env (for example `MULTICA_IMAGE_TAG`)
- Running services and status
- Local branch status relative to origin

Recommended commands:

```bash
cd <source_repo>
git status -sb
git rev-parse --short HEAD
git branch -vv
git log --oneline -n 5

# Check local branch vs origin/main
git fetch origin
git rev-list --left-right --count qaihub_multica...origin/main

cd <private_deploy_dir>
grep -n '^MULTICA_IMAGE_TAG=' .env
docker-compose ps
```

**Phase 1 Output - Local Branch Status Section:**

Include this before proceeding:

```
Current Branch: qaihub_multica
Latest Commit: <hash> "<message>"
Commits ahead of origin/main: <N>
Commits behind origin/main: <M>
Local uncommitted changes: <yes/no>
Unpushed commits in qaihub_multica: <N>
```

Preflight guardrails (required before any build/restart):

- Identify the actual running compose project from container labels instead of assuming the source repo path.
- Verify the deployment working directory from `com.docker.compose.project.working_dir`.
- Verify version source from deployment `.env` (`MULTICA_IMAGE_TAG`) and running container image tags.
- If source repo path and deploy path differ, always execute build/restart in deploy path only.
- **For local branch workflow: ensure all local work is committed to qaihub_multica before proceeding with merge/rebase.**

Example commands:

```bash
# discover real deploy project/path from running containers
docker ps --format '{{.Names}} {{.Label "com.docker.compose.project"}} {{.Label "com.docker.compose.project.working_dir"}} {{.Label "com.docker.compose.project.config_files"}}' | grep multica-private

# fixed deploy path for this environment:
# /home/q/docker/multica/multica_private
# Do not guess path variants in this environment.

cd <private_deploy_dir>
grep -n '^MULTICA_IMAGE_TAG=' .env
grep -nE 'image:.*multica-private-(backend|web|mcp)' docker-compose.yml
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep multica-private
```

### Phase 2: Delta Analysis (qaihub_multica vs origin/main)

Compare local branch baseline against latest `origin/main` and summarize by category.

Required outputs:

- Commit count: how many commits ahead/behind origin/main
- Total file/line diff stats between branches
- Top changed directories (in the delta)
- Bug-fix highlights on main (fix commits grouped by module)
- Critical path files related to user's concern (if provided)
- **Local-only commits** (commits only in qaihub_multica, not in origin/main)

Recommended commands:

```bash
cd <source_repo>
git fetch origin

# commits ahead/behind
git rev-list --left-right --count qaihub_multica...origin/main

# diff stats: qaihub_multica vs origin/main
git diff --shortstat qaihub_multica...origin/main

# top changed dirs
git diff --dirstat=files,0,cumulative qaihub_multica...origin/main | sort -nr | head -n 25

# commits only in local branch (not in main)
git log --oneline --no-merges qaihub_multica --not origin/main

# commits only in main (not in local branch)
git log --oneline --no-merges origin/main --not qaihub_multica

# optional: fix-only extraction from main
git log --oneline --no-merges origin/main --not qaihub_multica | grep -Ei '\bfix(\(|:|\b)' | head -n 20
```

### Phase 3: Decision Gate (Ask Before Merge/Rebase)

After presenting analysis, first provide an **AI Recommendation**, then ask **two** clear decision questions.

Required AI Recommendation block:

```
AI Recommendation: Upgrade now | Defer for now
Confidence: High | Medium | Low
Reasoning:
- Change risk level (low/medium/high)
- Business/operational impact
- Upgrade urgency (e.g. critical fixes included or not)
- Expected conflict probability for qaihub_multica
Suggested action:
- If upgrade now: proceed with merge
- If defer: keep current version and define next review window
```

Recommendation rules:

- The AI must make a clear recommendation and cannot stay neutral.
- If there are many fix/security/stability commits and local divergence is small, default to **recommend upgrade now (merge)**.
- If conflict risk is high or runtime stability risk is uncertain, recommend staged validation or defer with a concrete window.

Then ask two decision questions:

1. **Merge Strategy**: Would you prefer to:
   - `merge`: Preserves commit history, creates merge commit (recommended for formal tracking)
   - `rebase`: Linear history, replays local commits on top of main (recommended for clean history)

2. **Proceed**: Based on the change summary above and chosen strategy, do you want to proceed now?

Rules:

- Do not run merge/rebase/build commands before user confirms **both** strategy and proceed decision.
- If user says no, stop and provide a rollback-safe recommendation (for example, keep current, schedule window, or test in staging).
- **Strategy default recommendation**: For self-hosted scenarios with local patches → suggest **merge** (preserves audit trail) unless user prefers **rebase** for linear history.
- **Default action recommendation**: In this environment, if analysis shows substantial upstream fixes and only a few local self-host commits, recommend **execute merge upgrade now**.

### Phase 4: Upgrade Execution and Post-Upgrade Report

After explicit confirmation of strategy and decision:

**Step 4.1: Merge or Rebase**

```bash
cd <source_repo>
git fetch origin

# Option A: Merge (preserves history)
git merge --no-ff origin/main -m "merge: upgrade to latest main with qaihub_multica local changes"

# Option B: Rebase (linear history)
git rebase origin/main

# If conflicts occur, resolve them:
# - For merge: git merge --continue or git merge --abort
# - For rebase: git rebase --continue or git rebase --abort
```

**Step 4.2: Build and Restart**

```bash
cd <private_deploy_dir>
docker-compose build <services>
docker-compose up -d <services>
docker-compose ps

# required post-upgrade version verification
grep -n '^MULTICA_IMAGE_TAG=' .env
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep <compose_project_name>
```

**Required outputs for this phase:**

- Merge/rebase result: successful, conflicted (with resolved files listed), or aborted
- Pre-upgrade deployed tag (from running container images and/or `.env`)
- Post-upgrade deployed tag (running container images)
- Whether tags match expected target commit/tag
- System service version matrix (service, running image tag, expected tag, match/mismatch)
- If available, application-reported version endpoint result
- **Local branch tip** after merge/rebase (new HEAD commit)
- **Whether local commits are intact** (list key local commits that were replayed or merged)

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

# show final local branch state
cd <source_repo>
git log --oneline -n 5
git branch -vv
```

## Reporting Format (Required)

Always provide results in the following sections:

1. "Local Branch State (Before Upgrade)"
- Branch: qaihub_multica
- HEAD commit
- Commits ahead of origin/main
- Local uncommitted changes: yes/no

2. "Upgrade Decision Inputs"
- Baseline version (deployed tag)
- Main target commit
- Delta size and top modules
- Local-only commits count

3. "Bug Fix Summary"
- Grouped by module: daemon/execenv, comments, cli/server, inbox/issues, desktop/auth, etc.
- Mention representative commits from main

4. "Upgrade Strategy Selected"
- merge or rebase
- Rationale (if user specified)

5. "AI Recommendation"
- Upgrade now or defer
- Confidence level
- Top reasons (benefit/risk/urgency/conflict probability)

6. "Decision"
- User confirmed or declined
- If declined, why

7. "Executed Changes" (only when upgraded)
- Merge/rebase command used
- Merge/rebase result: success/conflict/aborted
- Conflicted files (if any) and how resolved
- Pulled/replayed commits
- Built/restarted services
- Any service skipped and why

8. "Local Branch State (After Upgrade)"
- HEAD commit (new)
- Commits ahead of origin/main (updated count)
- Key local commits preserved: <list>

9. "Impact and Risk"
- Functional impact
- Operational impact (downtime/restart)
- Compatibility concerns
- Conflict resolution notes (if any)
- Known follow-up checks

10. "Validation"
- Service status checks
- Smoke test endpoints or UI checks
- System service version checks (image tag and app-reported version when available)
- Verify qaihub_multica branch is on latest commit

## Local Branch + Merge/Rebase Conflict Handling

### Before Merge/Rebase

1. Ensure all local changes are committed:
   ```bash
   git status
   # If dirty, commit or stash
   git add .
   git commit -m "chore: save local state before merge/rebase"
   ```

2. Fetch latest main:
   ```bash
   git fetch origin
   ```

### During Conflict

If merge or rebase conflicts occur:

1. Identify conflicted files:
   ```bash
   git status | grep "both modified"
   ```

2. Review conflicts:
   ```bash
   git diff --name-only --diff-filter=U
   ```

3. Resolve strategy:
   - **For self-hosted patches**: Keep local version (qaihub_multica) unless file is critical upstream change
   - **For deployment config**: Manual merge recommended (review both versions)
   - **For app code**: Prefer upstream version, manually re-apply self-host deltas

4. Complete merge/rebase:
   ```bash
   # After resolving conflicts:
   git add <resolved_files>
   
   # For merge:
   git merge --continue
   
   # For rebase:
   git rebase --continue
   ```

### Abort if Needed

```bash
# For merge
git merge --abort

# For rebase
git rebase --abort

# Both leave qaihub_multica unchanged
```

### Required Output on Conflict

- Conflicted files list
- Resolution decision for each file
- How self-host changes were preserved or lost
- Whether merge/rebase completed successfully after resolution
- Whether local patches remain intact

## Post-Upgrade Patch Re-Application (If Needed)

If you had local patches before merge/rebase and they were lost:

1. Identify patch commits (from git reflog or local branch backup):
   ```bash
   git reflog
   git log --all --oneline | grep <patch_message>
   ```

2. Cherry-pick lost patches:
   ```bash
   git cherry-pick <patch_commit_hash>
   ```

3. Recommit if needed:
   ```bash
   git add .
   git commit -m "chore(selfhost): re-apply local patch after merge/rebase"
   ```

## Safety Rules

- Never discard unrelated local changes without explicit approval.
- Prefer targeted service rebuilds over full-stack rebuilds unless necessary.
- If one service cannot be built, continue safely for unaffected services and clearly report the blocker.
- If deployment config references missing paths (for example missing Dockerfile), stop and report exact path mismatch with a concrete fix.
- Never run compose build/up from source repo by default; first resolve and use the real deploy directory.
- For this environment, use fixed deploy directory: /home/q/docker/multica/multica_private (do not auto-guess variants).
- **For local branch workflow**: Always commit local changes before merge/rebase. Do not leave working directory dirty.
- If a wrong compose project was started by mistake, stop and remove only that wrong project (`docker-compose down --remove-orphans` in that project), and do not touch the active private deployment project.
- If port conflict occurs (for example `0.0.0.0:5432 already in use`), treat it as a path/project mismatch first, then re-check running project labels before retrying.
- **Do not force-push to qaihub_multica** unless explicitly approved by user (preserve remote backup if remote tracking exists).

## Example Use Cases

- "Compare qaihub_multica with latest main, then ask me to confirm merge strategy before upgrading."
- "I have local changes on qaihub_multica. Should I rebase or merge when upgrading to main?"
- "Show me what will change if I rebase qaihub_multica on top of main, then let me decide."
- "在 qaihub_multica 分支上工作，需要从 main 上吸收最新更新，先比对再合并或变基。"
- "先评估 qaihub_multica 和 main 的差异，然后我决定是否合并或变基升级。"
