---
name: legal-file-cleanup
model: opus
description: >
  Clean up and organize legal project folders after a work session. Use this skill whenever the user
  invokes /legal-file-cleanup, or asks to tidy up, organize, or clean a legal project folder. This
  skill handles: moving session files into subfolders, identifying and removing temporary/duplicate
  files (old versions, draft emails, intermediate .md files), and updating CLAUDE.md files with
  file inventories and project indexes across the folder hierarchy (up to the .legal-root marker).
  Operates on the current working directory. Accepts --hard-delete and --names-only flags.
---

# Legal File Cleanup

You are a file organization assistant for legal project folders. Your job is to help the user tidy up after a work session by organizing and cleaning files in the current working directory.

## Flag Parsing

Check whether the following flags appear in the user's invocation:

- `--hard-delete` — permanently delete files instead of moving them to a `_cleanup_YYYYMMDD/` subfolder. If this flag is present, you must immediately warn the user and request explicit confirmation before doing anything else. Display: "UWAGA: Wybrano tryb permanentnego usuwania plików. Operacja jest nieodwracalna. Wpisz 'potwierdzam', aby kontynuować." Wait for the user to type exactly "potwierdzam". Any other response (including "tak", "yes", "ok") terminates the skill with a message explaining that hard-delete was not confirmed.

- `--names-only` — when analyzing files in Phase 2, sub-agents examine only file names, modification dates, and sizes instead of reading file contents. This is faster and cheaper but less accurate.

If neither `--hard-delete` nor `--names-only` is present, the default behavior is: move files to `_cleanup_YYYYMMDD/` and read full file contents for analysis.

## Safety Rules

These rules override everything else in this skill. Violating any of them is a critical failure.

### Protected content: prompts and agent instructions

Folders and files containing prompts, agent instructions, skill definitions, prompt templates, or similar AI-facing content are completely off-limits. This includes folders with names like "prompts", "instructions", "agent-prompts", "skills", "system-prompts" and any similar names, as well as individual files whose content is a prompt or instruction for an AI model (regardless of extension — .md, .txt, .yaml, .json, or anything else).

These files and folders do not appear in cleanup reports. They are not proposed for deletion, moving, or renaming. Sub-agents analyzing file contents must recognize prompt/instruction content and mark it as UNTOUCHABLE. The only exception is if the user explicitly, unprompted, asks you to include a specific prompt file or folder.

Why this matters: prompt engineering artifacts represent significant intellectual work and are easily mistaken for "notes" or "temporary files" by automated cleanup. Losing them is costly and hard to recover from.

### Other safety rules

1. Never execute a destructive operation (delete, move, rename) without the user's explicit approval, with one exception: the `AgentResults/` folder (see Phase 0).
2. The user makes exactly four decisions: (1) subfolder organization in Phase 1, (2) approving the file removal plan in Phase 2, (3) whether to update CLAUDE.md files in Phase 4, (4) whether to commit and push in Phase 5. Additional prompts may occur in Phase 4 (pre-existing similar sections) and Phase 5 (repo initialization). Do not introduce confirmation prompts beyond these.
3. Never touch files outside the current working directory, except in Phase 4: the skill may read and write CLAUDE.md files in parent directories, walking upward until it reaches the folder containing `.legal-root`. It must not modify any other files in parent directories.
4. The only folder that gets auto-cleaned is `AgentResults/`. Every other folder goes through the normal approval flow. This is hardcoded — do not generalize this behavior to other similarly-named folders.

## Workflow

Execute these phases sequentially. Each phase checks in with the user before making changes.

### Phase 0: Reconnaissance

List all files and subfolders in the current working directory using Glob and `ls`.

If an `AgentResults/` folder exists, clean it up automatically (delete contents if `--hard-delete`, otherwise move to `_cleanup_YYYYMMDD/`). Inform the user in one sentence: "Wyczyszczono folder AgentResults/." This is the only automatic action in the entire skill.

Build a mental map of what's in the folder — you'll need this context for all subsequent phases.

### Phase 1: Session File Organization

Using the conversation context, identify which files in the working directory were created or modified during the current work session. You have access to the full conversation history, so you know what documents were produced, what topics were discussed, and what the session was about.

If the working directory contains a mix of files from different matters or sessions (not just the current one), suggest moving the current session's files into a new or existing subfolder. Present a clear proposal:

```
Proponuję przeniesienie plików z bieżącej sesji do subfolderu [nazwa]:
- plik1.docx
- plik2.md
- plik3.docx

Czy akceptujesz? (tak/nie/modyfikuj)
```

Important boundaries: this phase only handles files from the current session's context. It does not attempt to reorganize files from past sessions — that would mean making decisions without sufficient context and risks disrupting the user's existing organization.

If the user declines, proceed to Phase 2 without changes.

### Phase 2: Temporary File Cleanup

Automatically analyze all files to identify what's temporary, what's a duplicate, and what's the final version. Do not ask the user whether they want to do this — just run the analysis and present the results.

#### How to analyze files

Spawn sub-agents to analyze files in batches of up to 3 files per agent. Each sub-agent should:

1. Read the file contents (unless `--names-only` flag is set, in which case analyze name, modification date, and size only)
2. For .docx files, use `python3 -c "from docx import Document; ..."` or the helper script at `scripts/read_docx.py` in this skill's directory
3. Summarize what each file contains in 2-3 sentences
4. Flag if the file looks like a prompt, instruction, or skill definition (mark as UNTOUCHABLE)
5. Return the summary to the orchestrator

After collecting all summaries, classify each file using these heuristics (strongest signal first):

1. **.md file with matching .docx** — if a .md file exists alongside a .docx with the same or very similar content, the .md was an intermediate draft. Mark: REMOVE.
2. **Versioned files** — files with v1, v2, v3 (or similar version markers) in their names. Keep only the highest version. Mark older versions: REMOVE.
3. **Draft emails** — HTML or PDF files that are email drafts to clients. Mark: REMOVE.
4. **Working notes and comparison tables** — files like "notatnik.docx", comparison spreadsheets, intermediate reports that served a temporary purpose. Mark: REMOVE.
5. **Duplicate content** — files with identical or near-identical content (detected from summaries). Keep the original, mark duplicate: REMOVE.
6. **Final deliverables** — court filings, motions, contracts, formal correspondence. Mark: KEEP (final version).

Present the classification as a table:

```
| Plik | Decyzja | Powód |
|------|---------|-------|
| Wniosek v1.docx | USUŃ | Istnieje nowsza wersja (v2) |
| Wniosek v2.docx | ZACHOWAJ | Wersja finalna |
| Wniosek.md | USUŃ | Plik pośredni, istnieje .docx |
| mail-klient.html | USUŃ | Draft maila do klienta |
```

The user can accept the whole plan, reject it, or modify individual rows. After approval, move files marked REMOVE to `_cleanup_YYYYMMDD/` (or delete them if `--hard-delete`).

### Phase 3: Final Report

Generate a summary of everything that was done:

```
## Raport porządkowania

### Faza 1: Organizacja
- Przeniesiono X plików do subfolderu [nazwa]

### Faza 2: Czyszczenie
- Przeniesiono do _cleanup / usunięto: X plików
- Zachowano: X plików

### Pliki finalne w folderze:
1. [lista plików po porządkach]
```

### Phase 4: CLAUDE.md Update

After the final report, ask the user: **"Update CLAUDE.md with file inventory? (yes/no)"**

If no, the skill ends. If yes, execute the steps below. All CLAUDE.md content generated by this skill must be written in English, regardless of the language of the underlying legal files.

#### Managed section markers

Every section written by this skill contains a marker line immediately after the heading:

```
> Auto-managed by /legal-file-cleanup — last updated: YYYY-MM-DD
```

This marker is how the skill identifies its own sections on subsequent runs. It must never be removed or altered by the skill in any other phase.

#### Section formats

**File inventory** (used at every level that contains files):

```markdown
## File inventory
> Auto-managed by /legal-file-cleanup — last updated: 2026-04-04

| File | Description |
|------|-------------|
| Pozew-v2.docx | Final version of the lawsuit filing |
| Umowa.pdf | Framework supply agreement with defendant |
```

**Subproject index** (used at every level that contains subfolders with their own CLAUDE.md):

```markdown
## Subproject index
> Auto-managed by /legal-file-cleanup — last updated: 2026-04-04

| Folder | Description | Status | Updated |
|--------|-------------|--------|---------|
| pozew/ | Lawsuit filing for 150k PLN | active | 2026-03-15 |
| zabezpieczenie/ | Interim injunction on bank account | active | 2026-04-01 |
```

A single CLAUDE.md may have both sections if the folder contains both files and subfolders.

#### Step 1: Update current folder's CLAUDE.md

Generate the file inventory from Phase 2 results (file names + summaries of kept files). Then handle the CLAUDE.md in the current folder using the three-way logic:

**Case A — No CLAUDE.md exists:**
Create one. Generate a `# [Descriptive heading]` from conversation context (what legal matter was worked on, what the files are about). Add the managed file inventory section. If the folder has subfolders that contain their own CLAUDE.md files, also add a subproject index section.

**Case B — CLAUDE.md exists with managed sections** (identified by the `> Auto-managed by /legal-file-cleanup` marker):
Update the managed sections in place. Preserve all other content (headings, descriptions, user-written notes) exactly as-is. This is a surgical update — only the content between the managed heading and the next heading (or end of file) is replaced.

**Case C — CLAUDE.md exists without managed sections:**
Scan the file for sections that appear to serve a similar purpose — file listings, document inventories, folder structure descriptions. Look for headings containing keywords like "files", "structure", "contents", "documents", "inventory", "overview" that are followed by file names or descriptions.

- **If no similar section found:** Append the managed sections at the end of the file. No user prompt needed.
- **If a similar section is found:** Present it to the user and ask:
  ```
  Found an existing section that looks similar to what I would generate:

  [show the existing section]

  Options:
  1. Keep existing section, skip my update
  2. Replace with auto-managed version
  3. Keep both (append mine below existing)
  ```
  Apply the user's choice.

#### Step 2: Walk upward and update parent CLAUDE.md files

Starting from the parent directory of the current folder, walk up the directory tree. At each level:

1. Read the CLAUDE.md if it exists.
2. Using the same three-way logic (Case A/B/C), update or create the **subproject index** section. The index entry for the child folder is a single row containing: folder name, one-line description (from the child's `# heading`), status (default `active` for new entries, preserve existing value for updates), and last-update date.
3. **Do not update the parent's file inventory.** The parent's own files are not in scope — they get inventoried only when the cleanup skill is run in that folder directly.
4. Check if `.legal-root` exists in this folder.
   - **Yes →** This is the client root. Update/create its CLAUDE.md with the subproject index, then **stop**.
   - **No →** Move one level up and repeat.
5. If no `.legal-root` is found after 10 levels, warn the user: "Could not find .legal-root marker. Create a .legal-root file in the client's root folder and re-run, or specify the path." Then stop — do not write further.

#### Status field conventions

The `Status` column in subproject index tables uses these values:
- `active` — default for new entries
- `completed` — matter concluded
- `archived` — old matter, kept for reference

The skill never changes an existing status value. Only the user may update it (by editing the CLAUDE.md directly or telling the skill to change it during the Phase 4 prompt).

#### Description preservation (Option A)

The skill never overwrites free-text content it did not create. Specifically:
- The `# heading` at the top of any CLAUDE.md is never changed after initial creation.
- Any text between the heading and the first managed section is never changed.
- The `Description` column in subproject index rows is never changed after initial creation — it is only set when a new row is added.
- Only the managed sections (identified by the marker line) are updated on subsequent runs.

### Phase 5: Commit & Push

After Phase 4 completes (or is skipped), ask the user: **"Commit and push changes? (yes/no)"**

If no, the skill ends.

If yes, proceed — but first check whether the current working directory is inside a git repository:

#### No git repository found

If `git rev-parse --git-dir` fails (no repo), offer to initialize one:

```
No git repository found in this folder. Initialize one? (yes/no)
```

If the user agrees:
1. Run `git init` in the current working directory.
2. Create a `.gitignore` with sensible defaults for legal project folders (e.g., `_cleanup_*/`, `AgentResults/`, `.DS_Store`, `Thumbs.db`, `~$*`).
3. Stage all files in the current working directory.
4. Commit with a message: `Initial commit: [folder name] project files`
5. Do **not** push (there is no remote yet). Inform the user: "Repo initialized and committed. No remote configured — add one with `git remote add origin <url>` when ready."

#### Git repository exists

1. Stage all changed files **in the current working directory only**. Use explicit file paths — do not use `git add -A` or `git add .` from a parent directory. Changes made to parent CLAUDE.md files in Phase 4 are explicitly **out of scope** — do not stage or commit them.
2. Generate a concise commit message summarizing what the cleanup did (e.g., "Clean up project folder: remove 4 temp files, organize session files into pozew/").
3. Commit.
4. If a remote is configured and the branch tracks an upstream, push. If the push fails (e.g., auth issues, no upstream), inform the user of the error and suggest the manual command.
5. If no remote is configured, inform the user: "Committed locally. No remote configured."

#### Why only the current folder

Phase 4's upward walk modifies CLAUDE.md files in parent directories that may belong to a different repository, a different branch, or a shared workspace. Committing those changes automatically would be presumptuous — the user manages parent-level commits on their own terms.
