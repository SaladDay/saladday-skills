# saladday-skills

我自己写的 Claude Code skill。

| skill | 做什么 |
|---|---|
| [saladday-pr-triage](skills/saladday-pr-triage/SKILL.md) | 扫一个仓库的 issue，挑出适合提 PR 的：问题真实存在、本机能测、没人在修、维护者会收。只出报告，不在 GitHub 上做任何操作。 |
| [saladday-pr-style](skills/saladday-pr-style/SKILL.md) | 给别人的仓库写修复和 PR：先用测试复现，改动点最窄，能删就不加，commit 和 PR 描述短而具体，push 前把证据给用户看。 |

两个一起用：先 `/saladday-pr-triage OWNER/REPO` 挑 issue，再 `/saladday-pr-style OWNER/REPO#123` 修。

## 安装

需要 `gh`（已登录）和 `python3`。

```sh
git clone https://github.com/SaladDay/saladday-skills ~/dev/saladday-skills
mkdir -p ~/.claude/skills
ln -s ~/dev/saladday-skills/skills/* ~/.claude/skills/
```

triage 的脚本路径写死为 `~/.claude/skills/saladday-pr-triage/scripts/list_issues.py`，所以要装在 `~/.claude/skills/` 下，不要改目录名。

更新：`git -C ~/dev/saladday-skills pull`。
