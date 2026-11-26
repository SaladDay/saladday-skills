# saladday-skills

Claude Code skills I wrote. The skill files themselves are in Chinese.

| skill | what it does |
|---|---|
| [saladday-pr-triage](skills/saladday-pr-triage/SKILL.md) | Scans a repo's issues and picks the ones worth a PR: the bug is real, can be tested locally, nobody is fixing it, and the maintainers would accept a fix. Reports only; takes no action on GitHub. |
| [saladday-pr-style](skills/saladday-pr-style/SKILL.md) | Writes the fix and PR for someone else's repo: reproduce with a failing test first, change the narrowest spot, prefer deleting code over adding it, keep the commit and PR description short and specific, and show the evidence to the user before pushing. |

They work as a pair: `/saladday-pr-triage OWNER/REPO` to pick an issue, then `/saladday-pr-style OWNER/REPO#123` to fix it.

## Install

Requires `gh` (logged in) and `python3`.

```sh
git clone https://github.com/SaladDay/saladday-skills ~/dev/saladday-skills
mkdir -p ~/.claude/skills
ln -s ~/dev/saladday-skills/skills/* ~/.claude/skills/
```

The triage skill calls its script at `~/.claude/skills/saladday-pr-triage/scripts/list_issues.py`, so install under `~/.claude/skills/` and keep the directory names.

Update with `git -C ~/dev/saladday-skills pull`.
