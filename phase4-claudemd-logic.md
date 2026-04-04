# Phase 4: CLAUDE.md Update Logic

Reference document for the `/legal-file-cleanup` skill. Loaded during Phase 4 execution.

## Managed section markers

Every section written by this skill contains a marker line immediately after the heading:

```
> Auto-managed by /legal-file-cleanup — last updated: YYYY-MM-DD
```

This marker is how the skill identifies its own sections on subsequent runs. It must never be removed or altered by the skill in any other phase.

## Section formats

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

## Step 1: Update current folder's CLAUDE.md

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

## Step 2: Walk upward and update parent CLAUDE.md files

Starting from the parent directory of the current folder, walk up the directory tree. At each level:

1. Read the CLAUDE.md if it exists.
2. Using the same three-way logic (Case A/B/C), update or create the **subproject index** section. The index entry for the child folder is a single row containing: folder name, one-line description (from the child's `# heading`), status (default `active` for new entries, preserve existing value for updates), and last-update date.
3. **Do not update the parent's file inventory.** The parent's own files are not in scope — they get inventoried only when the cleanup skill is run in that folder directly.
4. Check if `.legal-root` exists in this folder.
   - **Yes →** This is the client root. Update/create its CLAUDE.md with the subproject index, then **stop**.
   - **No →** Move one level up and repeat.
5. If no `.legal-root` is found after 10 levels, warn the user: "Could not find .legal-root marker. Create a .legal-root file in the client's root folder and re-run, or specify the path." Then stop — do not write further.

## Status field conventions

The `Status` column in subproject index tables uses these values:
- `active` — default for new entries
- `completed` — matter concluded
- `archived` — old matter, kept for reference

The skill never changes an existing status value. Only the user may update it (by editing the CLAUDE.md directly or telling the skill to change it during the Phase 4 prompt).

## Description preservation

The skill never overwrites free-text content it did not create. Specifically:
- The `# heading` at the top of any CLAUDE.md is never changed after initial creation.
- Any text between the heading and the first managed section is never changed.
- The `Description` column in subproject index rows is never changed after initial creation — it is only set when a new row is added.
- Only the managed sections (identified by the marker line) are updated on subsequent runs.
