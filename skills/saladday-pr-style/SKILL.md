---
name: saladday-pr-style
description: 给别人的仓库写修复和 PR 的规范：先用测试复现，改动点最窄，能删就不加，测试少而准，commit 和 PR 描述短而具体，提交前把证据给用户看。Use when user says "按我们的风格修", "写PR", "修这个issue", "saladday style", "fix this issue", or after saladday-pr-triage picks an issue.
argument-hint: "OWNER/REPO#ISSUE"
---

# saladday-pr-style

## 总原则

- **真实性优先**：先复现再改。必须在当前默认分支上用真正走该代码路径的失败测试或脚本跑出问题，把实际输出留下。只读代码或沿用他人分析不算复现。复现不了就停，不得把未验证的判断当成已确认的 bug 去修或写进 PR。
- 一个 PR 只修一个问题，小到维护者几分钟就能看完。
- **能删就不加**：两种修法都能修好时，选删代码的那种。这是用户自己的规矩。
- 每一行改动都要能回答：删了它，哪个测试会挂、哪个行为会变？答不上来就删掉。
- 只提自己亲手测过的东西。

## 0. 开工前

- 没走过 saladday-pr-triage 第 0 步的，先做那一步：读贡献规则、AI 政策、AGENTS.md 和 CLAUDE.md。仓库规定的流程照做，比如必须的检查、独立评审。
- 在完整克隆里开分支，不用 triage 的临时浅克隆。用户有写权限就用本仓库的分支，没有就用 fork。
- 跑代码时，把 HOME、应用的配置目录、构建输出目录都指向 `mktemp -d`。改了 HOME 时，`RUSTUP_HOME`、`CARGO_HOME` 要指回真实目录，否则工具链会重新下载。
- 几个 worktree 共用一个构建目录时，每次换 worktree 先清掉本包的产物（Rust 用 `cargo clean -p <包名>`）。不清的话，cargo 只看文件修改时间，可能直接跑上一个 worktree 编出来的程序，和 main 的对比也就不可信了。

## 1. 先复现

- 从默认分支最新代码拉新分支。triage 报告里有复现测试的，直接拿来用。
- 先写回归测试，跑一遍，确认它失败，而且失败的原因就是 issue 说的问题。把失败时的实际输出留下来。失败原因对不上，或复现不了，就停，不要继续改。
- 测试放进已有的测试文件，沿用已有的辅助函数和写法。测行为，不测实现细节。
- 边界只加真会走不同分支的。例如 `nil`、空字符串、`0` 各走一条路时才分别测。

## 2. 找最窄的改动点

从复现路径往回追，找到第一个出错的地方，改那里，不在外层兜底。

好的修法通常是：
- 去掉写死的值，改用已有的变量。例：菜单把 `LibraryItem.ALBUM` 写死了，换成传进来的 `type`，改 2 行。
- 删掉写错的特例或多余的判断。
- 在已有的错误分支里补上漏掉的情况。例：`EvalSymlinks` 遇到坏链接报 NotExist 时，按普通文件交给回调，不再中断整个遍历。
- 把无条件写入改成有条件写入。例：zoom 有值才放进请求参数，空值不再发出 `zoom=`。

不要的修法：加开关或配置项、加重试或超时盖住没查清的原因、吞掉异常、新增公开 API。

## 3. 删代码的边界

删代码优先，但只删和这个 bug 有关的：
- 删之前先 `git blame` 看来历。是有意写的（性能、兼容、遵守规范），删掉就是推翻原来的决定，必须在 PR 里明说并给理由；拿不准就不删。
- 顺手看到的死代码、不相关的重复，不在这个 PR 里删，记下来告诉用户，可以另开 PR。
- 不删测试，不删除或改名公开 API（库里 `pub` 的项也算），不删别人可能依赖的行为。
- 为了能测而抽出一个小函数可以，但抽完总行数不应明显变多。

## 4. 跟着仓库写

- 命名、错误处理、日志、注释口气照搬周围的代码。不改格式、不改名、不调整 import 顺序，除非格式化工具要求。
- 不加依赖。不改 CHANGELOG，除非仓库要求每个 PR 都写。
- 注释只在读代码看不出原因时写，只写为什么。
- 跑仓库自己的格式化、lint 和相关测试。

## 5. 自查

- 把修复撤掉，确认测试失败；放回修复，确认测试通过。
- 看 `git diff --stat`：正式代码超过约 50 行要说得清为什么。逐行过一遍新加的代码，能删的删掉。
- 跑完整的相关测试，不只跑新加的那个。
- 记下实际跑了哪些命令、结果如何、哪些没跑以及原因。

## 6. Commit

- 标题写修好以后的行为，不写改了哪个函数。前缀跟仓库惯例，看 `git log --oneline -30`：
  - `fix: keep broken symlinks from aborting store listing`
  - Go 仓库常用包路径：`internal/graphicsdriver/directx: avoid GPU waits between pixel writes and draws`
- 正文写两三句：原因、改法。不能只写 `Fixes #123`，要让以后翻历史的人不看 issue 也懂。
- 仓库要求 DCO 就用 `git commit -s`。
- 一个 commit 就够；评审后的修改另加 commit，标题说清改了什么。

## 7. PR 描述

有模板就照模板填。没有模板就用下面的格式，语言跟仓库，一般是英文。三个小标题分段，每段一到三句，测试用列表：

```
## Problem

<用户看到什么问题，原因是什么。>

## Fix

<怎么改的；删了什么也写出来。移植上游的写明上游 PR。>

Fixes #123

## Testing

- <新测试修复前失败、修复后通过>
- <实际跑的其他命令和结果>
- <没测到的部分和原因>
```

例子：

```
## Problem

Route mode wrote `PROXY_MANAGED` into `ANTHROPIC_API_KEY` for providers that keep their key there, such as OpenCode Go. Claude Code asks to confirm it as a custom API key; declining leaves the session logged out.

## Fix

The placeholder always goes into `ANTHROPIC_AUTH_TOKEN`, and takeover clears `ANTHROPIC_API_KEY`. Upstream requests are unchanged. Ports upstream #8111.

Fixes #554

## Testing

- New tests fail before the fix, pass after
- 6 tests expecting the old key updated
- `cargo fmt --check` passes
```

- 语言简洁直接，commit 正文也一样：
  - 短陈述句，主语是代码或行为；
  - 不用 "This PR..." 起头，不写总结套话，不复述 diff；
  - 每件事只说一次；
  - 确定的事不加 should、might。
- 改了界面就附修改前后的截图。
- 仓库要求声明 AI 使用就照要求声明；要求手动测试就真的手动测。

## 8. 交给用户

做到本地 commit 为止，把下面这些给用户看：
- diff 和 `git diff --stat`；
- 撤掉修复和放回修复时的测试输出；
- commit 信息和 PR 描述草稿；
- 没测到的部分。

用户确认前不 push、不开 PR、不在 issue 下评论。push 前再 `git fetch` 一次，查有没有人刚修了同一个问题：看 `git log HEAD..origin/main` 和 `gh pr list --state all --search "<issue 号或关键词>"`。已经有人修了就停下告诉用户，不再提。

PR 开出以后：
- 评审意见照改，另加 commit，回复只说改了什么。
- 维护者拒绝或者改用别的方案，就到此为止，不换个写法再提。
