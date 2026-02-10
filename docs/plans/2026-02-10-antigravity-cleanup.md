# Antigravity Cleanup Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove files and folders related to the Antigravity AI coding assistant and update references.

**Architecture:** Cleanup task.

**Tech Stack:** Bash

---

### Task 1: Remove Antigravity Files and Folders

**Files:**
- Delete: `.agent/`
- Delete: `AGENTS.md`
- Delete: `GEMINI.md`
- Delete: `apps/client/ai-todo.md`

**Step 1: Delete the files and folders**

Run:
```bash
rm -rf .agent AGENTS.md GEMINI.md apps/client/ai-todo.md
```

**Step 2: Verify deletion**

Run:
```bash
ls -a
ls apps/client/
```
Expected: Files/folders should not be listed.

**Step 3: Commit**

```bash
git add .
git commit -m "chore: remove Antigravity specific files and folders"
```

---

### Task 2: Remove References in CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Read CLAUDE.md to locate references**

Run:
```bash
grep -n "AGENTS.md" CLAUDE.md
```

**Step 2: Remove the Agent Roles section**

Remove the lines referencing `AGENTS.md` (likely under `## Agent Roles`).

```bash
# Example edit (adjust based on actual content)
# Remove:
# ## Agent Roles
# Refer to [AGENTS.md](file:///Users/hexa/projects/temp/gcs-lms/AGENTS.md) for agent definitions.
```

**Step 3: Verify changes**

Run:
```bash
cat CLAUDE.md
```
Expected: No "Agent Roles" section or `AGENTS.md` reference.

**Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "chore: remove AGENTS.md reference from CLAUDE.md"
```

---

### Task 3: Remove References in Playbook

**Files:**
- Modify: `apps/client/docs/playbook.md` (if applicable)

**Step 1: Search for references**

Run:
```bash
grep -r "AGENTS.md" apps/client/docs/playbook.md
```

**Step 2: Remove references if found**

If found, remove the line/section. If not found, skip this step.

**Step 3: Commit (if changes made)**

```bash
git add apps/client/docs/playbook.md
git commit -m "chore: remove AGENTS.md reference from playbook" || echo "No changes to commit"
```

---

### Task 4: Final Search and Cleanup

**Files:**
- Search entire codebase

**Step 1: Search for remaining references**

Run:
```bash
grep -r "AGENTS.md" .
grep -r "GEMINI.md" .
grep -r ".agent" .
```

**Step 2: Address any findings**

If any relevant references remain in documentation or config files, remove them.
(Note: Ignore `grep` output for the plan file itself or git history)

**Step 3: Commit (if changes made)**

```bash
git add .
git commit -m "chore: final cleanup of Antigravity references" || echo "No changes to commit"
```
