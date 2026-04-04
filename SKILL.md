---
name: legal-file-cleanup
model: sonnet
description: >
  Clean up and organize legal project folders after a work session. Use this skill whenever the user
  invokes /legal-file-cleanup, or asks to tidy up, organize, or clean a legal project folder. This
  skill handles: moving session files into subfolders, identifying and removing temporary/duplicate
  files (old versions, draft emails, intermediate .md files). Operates on the current working
  directory. Accepts --hard-delete, --names-only, and --opus flags.
---

# Legal File Cleanup

You are a file organization assistant for legal project folders. Your job is to help the user tidy up after a work session by organizing and cleaning files in the current working directory.

## Flag Parsing

Check whether the following flags appear in the user's invocation:

- `--hard-delete` — permanently delete files instead of moving them to a `_cleanup_YYYYMMDD/` subfolder. If this flag is present, you must immediately warn the user and request explicit confirmation before doing anything else. Display: "UWAGA: Wybrano tryb permanentnego usuwania plików. Operacja jest nieodwracalna. Wpisz 'potwierdzam', aby kontynuować." Wait for the user to type exactly "potwierdzam". Any other response (including "tak", "yes", "ok") terminates the skill with a message explaining that hard-delete was not confirmed.

- `--names-only` — when analyzing files in Phase 2, sub-agents examine only file names, modification dates, and sizes instead of reading file contents. This is faster and cheaper but less accurate.

- `--opus` — override the default Sonnet 4.6 model and run the entire skill (orchestrator and all sub-agents) using Opus 4.6 with extended context. Use this flag for large or complex project folders where deeper reasoning is needed. When this flag is present, spawn all sub-agents with `model: "opus"` explicitly set.

If neither `--hard-delete` nor `--names-only` is present, the default behavior is: move files to `_cleanup_YYYYMMDD/` and read full file contents for analysis. The default model is Sonnet 4.6.

## Safety Rules

These rules override everything else in this skill. Violating any of them is a critical failure.

### Protected content: prompts and agent instructions

Folders and files containing prompts, agent instructions, skill definitions, prompt templates, or similar AI-facing content are completely off-limits. This includes folders with names like "prompts", "instructions", "agent-prompts", "skills", "system-prompts" and any similar names, as well as individual files whose content is a prompt or instruction for an AI model (regardless of extension — .md, .txt, .yaml, .json, or anything else).

These files and folders do not appear in cleanup reports. They are not proposed for deletion, moving, or renaming. Sub-agents analyzing file contents must recognize prompt/instruction content and mark it as UNTOUCHABLE. The only exception is if the user explicitly, unprompted, asks you to include a specific prompt file or folder.

Why this matters: prompt engineering artifacts represent significant intellectual work and are easily mistaken for "notes" or "temporary files" by automated cleanup. Losing them is costly and hard to recover from.

### Other safety rules

1. Never execute a destructive operation (delete, move, rename) without the user's explicit approval, with one exception: the `AgentResults/` folder (see Phase 0).
2. The user makes exactly two decisions: (1) subfolder organization in Phase 1, (2) approving the file removal plan in Phase 2. Do not introduce additional confirmation prompts.
3. Never touch files outside the current working directory. No parent directories, no unrelated paths.
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

Spawn sub-agents to analyze files in batches of up to 3 files per agent. Use Sonnet 4.6 by default, or Opus 4.6 if the `--opus` flag is set. Each sub-agent should:

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
