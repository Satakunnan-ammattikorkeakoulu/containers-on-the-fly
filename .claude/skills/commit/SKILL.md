---
name: commit
description: Prepare a git commit message for staged changes
---

Review only the staged changes (`git diff --cached`), then prepare a conventional commit message following the project's commit format from CLAUDE.md.

**Keep the message tight.** Prefer short bullets over prose:
- Each bullet is one short line naming what changed — not a paragraph explaining why.
- Drop rationale that the diff or code itself already makes obvious.
- Collapse related sub-points into a single bullet.
- The PR description is the place for the longer "why" — the commit body should be scannable in a few seconds.
- If the change is small (one file, one concept), a single-line subject with no body is often right.

Present the message for my review before committing. Do NOT commit automatically — wait for my approval first.
