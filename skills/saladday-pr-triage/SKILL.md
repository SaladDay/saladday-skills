---
name: saladday-pr-triage
description: 扫一个 GitHub 仓库的 issue，挑出适合提 PR 的：问题真实存在、本机能测、没人在修、维护者会收；输出排好序的候选报告，不在 GitHub 上做任何操作。Use when user says "找能提PR的issue", "看看哪些issue适合修", "挑issue", "issue triage", "find issues to fix", or gives a repo and asks what to contribute.
argument-hint: "OWNER/REPO [issue numbers...]"
---

# saladday-pr-triage

在一个仓库里找出真实存在、改动小、我们能测、维护者会收的 issue。只出报告。选中以后用 saladday-pr-style 写修复。

## 第 0 步：仓库收不收

克隆到临时目录，列出写贡献规则的文件并整篇读完，README 里的 Contributing 一节也要读：

```
d=$(mktemp -d) && git clone -q --depth 200 https://github.com/OWNER/REPO "$d" && cd "$d"
ls -d CONTRIBUTING* AI_POLICY* AGENTS.md CLAUDE.md .github/CONTRIBUTING* .github/PULL_REQUEST_TEMPLATE* .github/pull_request_template* .github/copilot-instructions.md docs/*contribut* 2>/dev/null
grep -n -i -A12 '^#.*contribut' README*
```

遇到下面任一情况，整个仓库跳过，在报告里写明原因：
- 禁止 LLM 生成的代码或 PR 描述。
- 暂停接收外部 PR，或者不审没有贡献记录的新人。

记下这些，后面照做：
- AI 使用的条件，比如要声明、要手动测试；
- AGENTS.md、CLAUDE.md 里的流程和沙箱要求；
- 提 PR 前必须跑的检查，比如 fmt、lint、test；
- PR 模板、标题惯例（看 `git log --oneline -30`）、是否要签 CLA 或 DCO；
- 是否要求先在 issue 里讨论。这条在第 2 关按 issue 判断，不整库跳过。

如果 `gh api user -q .login` 就是 OWNER，说明这是用户自己的仓库：上面两条整库跳过的条件不适用，但 AGENTS.md、CLAUDE.md 里的流程照样遵守；后面说的"维护者"就是用户本人。

## 第 1 步：扫 issue

```
python3 ~/.claude/skills/saladday-pr-triage/scripts/list_issues.py OWNER/REPO --limit 100
python3 ~/.claude/skills/saladday-pr-triage/scripts/list_issues.py OWNER/REPO 123 456   # 只看指定 issue
```

每个 issue 一行，`filed_by` 说明是普通用户还是维护者提的，`maint_replied` 说明维护者回过没有。`status` 的含义：
- `BLOCK`：本仓库有开着的 PR、已分配给人、标签是 wontfix、question、needs-info 一类、维护者说过设计如此、复现不了、会自己做一类的话、维护者在等报告人回信息、有人在 60 天内认领。
- `CHECK`：已有合并的 PR，评论里提到了还没关闭的 PR，CONTRIBUTOR 身份的人说过上面那类话（常是没列成成员的维护者），或者认领已超过 60 天。
- `-`：没发现阻断信号。

flags 写成 `谁@日期: "关键词前后约 60 字"`，只是提示，会误报也会漏报。`BLOCK` 的 bug 报告先看这段引文，确认不是误报；`-` 和 `CHECK` 的要读完整讨论。读原文用：

```
gh issue view N -R OWNER/REPO --json title,body,comments --jq '"# " + .title, .body, (.comments[] | "--- \(.author.login) \(.createdAt[:10]): \(.body)")'
```

## 第 2 步：逐个过五关

先只看标题、标签和正文开头，把第 1 关能筛掉的筛掉，剩下的 bug 报告再读完整讨论。按顺序检查，卡在哪一关就停下，记下原因。

1. **范围**：
   - 功能请求、维护者自己的规划或跟踪类 issue，跳过。
   - 修复需要新增、删除或改名公开 API（库里 `pub` 的项也算）、配置项、命令或依赖，而维护者没在 issue 里同意，跳过。
   - 仓库要求先讨论方案，而这个 issue 还没讨论到位，跳过。
   - 文档只修事实错误，比如坏链接、错命令，不做补充说明；自己不懂的语言写的文档不碰。
2. **讨论状态**：
   - 维护者还在向报告人要信息，报告人没回，跳过。
   - 维护者说过按设计如此、不值得改、先搁置、方案没定、会自己做，跳过。
   - 维护者指出功能其实已经有、报告人只是没找到，跳过。这是用法问题，不该改代码。
   - 有人认领或已有 PR，跳过。脚本只认得关联过的 PR，再用关键词搜一遍：`gh pr list -R OWNER/REPO --state all --search "<关键词>"`。已关闭的 PR 要看为什么被关。
   - 已有的 PR 超过 60 天没动静、维护者也没评审过，不要另提一个，在报告里记下，由用户决定要不要去原 PR 下问。
3. **本机能不能测**：
   - bug 只出现在我们没有的环境里（某个系统、GPU、多显示器、真机、游戏、要付费账号的外部服务），跳过。测不了的不提。
   - 要跑代码时，把 HOME、应用的配置目录、构建输出目录（比如 `CARGO_TARGET_DIR`）都指向 `mktemp -d`，仓库有沙箱要求的照做。不碰用户真实的配置和正在运行的服务。
4. **是不是真问题**：
   - 在默认分支最新代码上复现，最好写成一个修复前会失败的测试，把测试代码留进报告。复现不了就跳过。
   - 克隆是浅的。issue 比克隆里最早的 commit 还早，或者下面 `git blame` 的行首带 `^`，先 `git fetch --unshallow` 再查。
   - 用 `git log --since=<issue 创建日期> -- <相关文件>` 看是不是已经修了。
   - 对要改的那几行 `git blame`，读引入它的 commit 和 PR。是有意这么写的（性能、兼容、遵守规范），跳过，除非维护者在 issue 里已经同意改。
   - commit 说明这段代码是从上游搬来的，就去上游看同一段代码和相关 PR：上游已经修了，移植过来是好候选；上游是有意这么写的，跳过。
   - issue 要求的改法和真正能测出来的 bug 不是一回事时，按 issue 原本的诉求下结论，另一个问题在报告里单独列为观察。
5. **根因清不清楚**：
   - 自己定位到出错的那一行，不照抄 issue 里的分析。报告人的诊断常常是错的。
   - 只能靠重试、加超时、加开关、吞掉异常来绕过的，说明根因没找到，跳过。
   - 根因在依赖库里的，找到依赖上游的 issue 或 PR 写进报告，跳过。

## 第 3 步：排序

五关都过了的，按下面的顺序排：
1. 主要靠删代码来修的排前面：删掉写错的特例、多余的判断、写死的值、重复的逻辑。
2. 预计正式代码改动越少越好；超过约 50 行要说明原因。
3. 维护者已确认是 bug、或报告人给了完整复现步骤的排前面。
4. 影响面大的排前面：+1 多、多人报告。

## 输出

先给一张表：

| issue | 结论 | 理由 | 预计改法 | 正式代码行数 +/- | 怎么测 |

再给每个候选写一小段：复现方式和结果、复现用的测试代码、根因在哪个文件哪个函数、打算怎么改（先说能删什么）、`git blame` 查到的来历。

然后按卡住的关分组，列出被跳过的 issue。只看标题就筛掉的可以合成一行。

一个候选都没有时，直说没有，再列出最接近的两三个和差在哪，以及过程中发现的其他问题。

## 不做的事

- 不在 issue 下评论、不认领、不开 PR、不 push，全部留给用户决定。
- 一个仓库一次最多推荐 3 个，宁缺毋滥。
- 维护者拒绝过的改法，不换个写法再推荐。
