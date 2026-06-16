---
name: sync_from_multica-ai
description: "Use when the user wants to sync this fork from multica-ai/multica. Default to GitHub Sync fork for simple upstream sync. First verify fork relationship, target branch, and whether the request is only to absorb upstream main changes. Only fall back to local git merge/rebase when Sync fork cannot satisfy the request. Keywords: sync fork, fork sync, sync from upstream, multica-ai, forked repo sync, 同步 fork, 从上游同步, sync_from_multica-ai"
---

# Sync From multica-ai Skill

## Purpose

Use the simplest safe path to sync this fork with upstream `multica-ai/multica`.

Default behavior:

1. Verify the repository is a GitHub fork of `multica-ai/multica`
2. Verify which branch the user wants to sync
3. If the goal is only to absorb upstream default branch updates into the fork default branch, recommend **GitHub `Sync fork`**
4. Only use local git merge/rebase workflow when GitHub `Sync fork` is not sufficient

This skill is intentionally biased toward not over-operating. If GitHub can do the sync directly, do not propose a heavier local upgrade workflow.

## Core Decision Rule

Prefer **GitHub `Sync fork`** when all of the following are true:

- The repository is a recognized fork of `multica-ai/multica`
- The user only wants to sync upstream changes
- The target is the fork's default branch or a branch GitHub can sync directly through the fork UI
- There is no requirement to preserve a special local integration flow beyond normal fork sync

Prefer **local git workflow** only when any of the following are true:

- The user needs to sync a non-default working branch such as `qaihub_multica`
- The fork relationship is missing or GitHub cannot offer `Sync fork`
- There are conflicts GitHub cannot resolve in the UI
- The user explicitly asks for merge, rebase, conflict handling, or deployment execution

## Mandatory Workflow

Do not jump to merge/rebase/build. First determine whether `Sync fork` is enough.

### Phase 1: Fork Sync Eligibility Check

Collect the minimum facts needed to decide whether GitHub UI sync is sufficient.

Required checks:

- Current branch
- Default branch
- Whether the repo is a fork of `multica-ai/multica`
- Whether the user is asking to sync the fork generally, or a specific local branch such as `qaihub_multica`
- Whether there are local uncommitted changes that matter for a local fallback workflow

Recommended commands:

```bash
cd <source_repo>
git status -sb
git branch -vv
git remote -v
git rev-parse --abbrev-ref HEAD
git symbolic-ref refs/remotes/origin/HEAD
git fetch upstream
git rev-list --left-right --count HEAD...upstream/main
```

If available, also verify the GitHub fork relationship from repository metadata or the GitHub page.
If `git symbolic-ref refs/remotes/origin/HEAD` fails, treat the default branch as unknown and fall back to the repository metadata or GitHub UI instead of assuming `origin/main`.

### Phase 1 Output

Always summarize in this format:

```text
Fork Source: multica-ai/multica | unknown
Current Branch: <branch>
Default Branch: <branch>
Requested Sync Target: <default branch | qaihub_multica | unknown>
Local Uncommitted Changes: <yes/no>
GitHub Sync fork Suitable: <yes/no>
```

### Phase 2: Recommendation

After the eligibility check, provide a direct recommendation.

Required recommendation block:

```text
AI Recommendation: Use GitHub Sync fork | Use local git merge/rebase
Confidence: High | Medium | Low
Reasoning:
- Why GitHub Sync fork is sufficient or insufficient
- Whether the request concerns only upstream default-branch sync
- Whether the current branch changes the recommended path
Suggested action:
- If Sync fork: click GitHub "Sync fork"
- If local workflow: compare branch divergence first, then choose merge or rebase
```

Recommendation rules:

- If the repo is a normal fork and the user only wants upstream sync, default to **Use GitHub Sync fork**
- If the user specifically mentions `qaihub_multica` or another working branch, default to **Use local git merge/rebase**
- If branch intent is ambiguous, explicitly state the ambiguity before recommending

### Phase 3: Decision Gate

Ask only the question that matches the recommendation.

If recommending GitHub Sync fork, ask:

1. Do you only want to sync the fork with upstream `main` on GitHub, without touching local deployment/build steps?

If recommending local workflow, ask:

1. Do you want to sync `qaihub_multica` by `merge` or `rebase`?
2. Do you want to proceed now?

Rules:

- Do not run merge/rebase/build commands before explicit confirmation
- Do not expand into deployment steps unless the user explicitly asks for build/deploy after sync
- If GitHub `Sync fork` is sufficient, stop after giving the recommendation unless the user asks for local execution help

## Local Fallback Workflow

Use this only when GitHub `Sync fork` is not enough.

### Fallback Phase A: Branch Delta Analysis

Compare the working branch against upstream main.

Recommended commands:

```bash
cd <source_repo>
git fetch upstream
git rev-list --left-right --count qaihub_multica...upstream/main
git diff --shortstat qaihub_multica...upstream/main
git diff --dirstat=files,0,cumulative qaihub_multica...upstream/main | sort -nr | head -n 25
git log --oneline --no-merges qaihub_multica --not upstream/main
git log --oneline --no-merges upstream/main --not qaihub_multica
```

Required outputs:

- Commits ahead/behind
- Local-only commits
- Main-only commits
- Top changed directories
- Conflict risk estimate

### Fallback Phase B: Merge or Rebase

Only after user confirmation:

```bash
cd <source_repo>
git fetch upstream

# merge option
git merge --no-ff upstream/main -m "merge: sync upstream main into qaihub_multica"

# rebase option
git rebase upstream/main
```

Conflict handling rules:

- Never discard local changes silently
- For local self-host patches, preserve local intent unless upstream change is clearly required
- If conflicts are non-trivial, stop and report exact files plus resolution options

### Optional Deployment Phase

Only run this if the user explicitly asks to rebuild or redeploy after sync.

For this environment, use deploy path:

```bash
/home/q/docker/multica/multica_private
```

Recommended commands:

```bash
cd /home/q/docker/multica/multica_private
docker-compose ps
docker-compose build <services>
docker-compose up -d <services>
```

## Reporting Format

Always provide results in these sections:

1. "Fork Sync Assessment"
- Fork source
- Current branch
- Default branch
- Requested sync target
- Whether GitHub `Sync fork` is suitable

2. "AI Recommendation"
- Use GitHub `Sync fork` or local git workflow
- Confidence
- Top reasons

3. "Decision Needed"
- Exact next user choice required

4. "Executed Changes"
- Only if any local git or deployment action was actually performed

5. "Impact and Risk"
- Whether this affects only repository history or also runtime deployment
- Conflict risk
- Any follow-up checks

## Safety Rules

- Default to the lightest valid sync path
- Do not recommend merge/rebase when GitHub `Sync fork` is enough
- Do not build or redeploy just because code sync was discussed
- Do not force-push any branch unless explicitly approved
- If the request is only about GitHub-side fork sync, keep the answer short and operational

## Example Use Cases

- "这个仓库是 fork 的，只需要 sync fork 吗？"
- "帮我判断是点 GitHub 的 Sync fork 就够，还是要本地 merge。"
- "我要把 fork 从 multica-ai/multica 同步过来。"
- "qaihub_multica 不是默认分支，应该 sync fork 还是 rebase？"
