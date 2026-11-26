#!/usr/bin/env python3
"""List a repo's open issues with the signals that rule a PR in or out.

usage: list_issues.py OWNER/REPO [--limit N] [ISSUE_NUMBER ...]

With numbers, checks only those (open or closed; PR numbers are skipped).
Read-only: it only calls `gh api graphql`. Flags are keyword hints; read the thread.
"""
import argparse, datetime, json, re, subprocess, sys

FIELDS = """
number title state createdAt authorAssociation body
author { login }
labels(first: 20) { nodes { name } }
assignees(first: 5) { nodes { login } }
reactions { totalCount }
comments(last: 50) { totalCount nodes { authorAssociation createdAt author { login } body } }
timelineItems(last: 50, itemTypes: [CROSS_REFERENCED_EVENT, CONNECTED_EVENT]) { nodes {
  ... on CrossReferencedEvent { source { ... on PullRequest { number state repository { nameWithOwner } } } }
  ... on ConnectedEvent { subject { ... on PullRequest { number state repository { nameWithOwner } } } }
} }
"""

MAINT = {"OWNER", "MEMBER", "COLLABORATOR"}
BLOCK_LABEL = re.compile(r"wont.?fix|won't|invalid|duplicate|question|discussion|needs?.?(info|repro|triage|decision|design|feedback)|blocked|on.?hold|postpone|stale|by.?design|not.?a.?bug|upstream|declined|rejected", re.I)
GOOD_LABEL = re.compile(r"bug|confirmed|accepted|good.first|help.wanted|regression", re.I)
# maintainer says no / not now / will do it themselves
SAYS_NO = re.compile(
    r"by design|is intended|as intended|intended behaviou?r|intentional|deliberate|expected behaviou?r|works as|not a bug|won'?t (fix|change)"
    r"|can'?t reproduce|cannot reproduce|unable to reproduce|do(es)? not (encounter|see|happen)|don'?t see"
    r"|already (fixed|supported|exists)|fixed (in|on|by)|no downside|why (is|are) (this|these|that)"
    r"|postpone|on hold|let'?s discuss|not agreed|need(s)? (more )?(discussion|design)|duplicate"
    r"|working on (this|it)|i'?ll (fix|take|handle)|we'?ll (add|do|implement|support)|on (the|our) roadmap|planned"
    r"|设计如此|故意|不是 ?bug|无法复现|复现不了|已修复|已经修复|重复|我来修|正在修|下一?个版本|我们会|在规划|计划中", re.I)
# maintainer waiting on the reporter: blocks only while the reporter hasn't answered
ASKS_INFO = re.compile(r"(could|can) you (post|run|share|provide|check|try|retest)|please (provide|post|share|retest)|请提供|能否提供|麻烦提供|再试一下", re.I)
CLAIM = re.compile(r"i'?d like to (work|take)|i'?ll (take|work|fix|open a pr)|can i (work|take)|assign (it to )?me|working on (this|it)|pr (is )?coming|opened a pr|submitted a pr|我来|我想认领|我在修|我提了 ?pr", re.I)
WITHDRAW = re.compile(r"never ?mind|can'?t reproduce|cannot reproduce|not (going|able) to|unassign|withdraw|giving up|放弃|不做了|复现不了", re.I)


def gql(query, **vars):
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in vars.items():
        cmd += ["-F", f"{k}={v}"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode:
        sys.exit(out.stderr.strip())
    return json.loads(out.stdout)["data"]["repository"]


def lookup(owner, name, numbers, fields):
    """Fetch issues or PRs by number, 40 per query."""
    found, numbers = {}, sorted(set(numbers))
    for k in range(0, len(numbers), 40):
        parts = " ".join(f"n{n}: issueOrPullRequest(number: {n}) {{ __typename {fields} }}" for n in numbers[k:k + 40])
        q = f"query($o:String!,$n:String!){{ repository(owner:$o,name:$n){{ {parts} }} }}"
        cmd = ["gh", "api", "graphql", "-f", f"query={q}", "-F", f"o={owner}", "-F", f"n={name}"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        out = json.loads(res.stdout or "{}")
        if res.returncode and not out.get("data"):  # partial errors (e.g. a missing number) still return data
            sys.exit(res.stderr.strip() or "gh api graphql failed")
        for v in ((out.get("data") or {}).get("repository") or {}).values():
            if v and "number" in v:  # items of the other type come back as only __typename
                found[v["number"]] = v
    return found


def fetch(owner, name, limit, numbers):
    if numbers:
        got = lookup(owner, name, numbers, f"... on Issue {{ {FIELDS} }} ... on PullRequest {{ number }}")
        for n in numbers:
            if n not in got or got[n]["__typename"] != "Issue":
                print(f"#{n}: not an issue, skipped", file=sys.stderr)
        return [v for v in got.values() if v["__typename"] == "Issue"]
    q = f"""query($o:String!,$n:String!,$k:Int!,$c:String){{ repository(owner:$o,name:$n){{
      issues(first:$k, after:$c, states:OPEN, orderBy:{{field:CREATED_AT, direction:DESC}}){{
        pageInfo {{ hasNextPage endCursor }} nodes {{ {FIELDS} }} }} }} }}"""
    issues, cursor = [], None
    while len(issues) < limit:
        args = dict(o=owner, n=name, k=min(50, limit - len(issues)))
        if cursor:
            args["c"] = cursor
        page = gql(q, **args)["issues"]
        issues += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return issues


def who(c):
    return f"{(c['author'] or {}).get('login', 'ghost')}@{c['createdAt'][5:10]}"


def quote(body, m):
    """About 60 characters around a keyword match, so a flag can be judged without opening the issue."""
    return " ".join(body[max(0, m.start() - 25):m.end() + 35].split())


def flags(i, repo, mentioned_prs):
    """Return (blocks, checks)."""
    block, check = [], []
    for t in i["timelineItems"]["nodes"]:
        pr = t.get("source") or t.get("subject") or {}
        # PRs in other repos (forks, Homebrew bumps) only mention the issue
        if not pr.get("number") or pr["repository"]["nameWithOwner"].lower() != repo.lower():
            continue
        if pr["state"] == "OPEN":
            block.append(f"open PR #{pr['number']}")
        elif pr["state"] == "MERGED":
            check.append(f"merged PR #{pr['number']}")
    for n, state in mentioned_prs:
        if f"open PR #{n}" not in block and f"merged PR #{n}" not in check:
            check.append(f"mentions {state.lower()} PR #{n}")
    if i["assignees"]["nodes"]:
        block.append("assigned " + ",".join(a["login"] for a in i["assignees"]["nodes"]))
    block += [f"label:{l['name']}" for l in i["labels"]["nodes"] if BLOCK_LABEL.search(l["name"])]

    reporter = (i["author"] or {}).get("login")
    comments = i["comments"]["nodes"]
    today = datetime.date.today()
    for k, c in enumerate(comments):
        body, assoc, login = c["body"] or "", c["authorAssociation"], (c["author"] or {}).get("login")
        later = comments[k + 1:]
        if assoc in MAINT or assoc == "CONTRIBUTOR":  # CONTRIBUTOR is often an unlisted maintainer
            dest = block if assoc in MAINT else check
            if m := SAYS_NO.search(body):
                dest.append(f'{who(c)}: "{quote(body, m)}"')
            elif (m := ASKS_INFO.search(body)) and not any((x["author"] or {}).get("login") == reporter for x in later):
                dest.append(f'{who(c)}: "{quote(body, m)}", no reply')
        elif CLAIM.search(body) and login != reporter:
            if any((x["author"] or {}).get("login") == login and WITHDRAW.search(x["body"] or "") for x in later):
                continue
            age = (today - datetime.date.fromisoformat(c["createdAt"][:10])).days
            (check if age > 60 else block).append(f"claimed {who(c)}" + (" (stale)" if age > 60 else ""))
    return sorted(set(block)), sorted(set(check))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("numbers", nargs="*", type=int)
    ap.add_argument("--limit", type=int, default=100)
    a = ap.parse_args()
    owner, name = a.repo.split("/")
    issues = fetch(owner, name, a.limit, a.numbers)

    # PRs linked only by "#N" or a /pull/N URL in the body or comments
    pr_ref = re.compile(rf"(?<![\w/])#(\d+)\b|github\.com/{re.escape(a.repo)}/pull/(\d+)", re.I)
    refs = {}
    for i in issues:
        text = " ".join([i["body"] or ""] + [c["body"] or "" for c in i["comments"]["nodes"]])
        refs[i["number"]] = {int(x or y) for x, y in pr_ref.findall(text)} - {i["number"]}
    prs = lookup(owner, name, set().union(*refs.values()) if refs else [], "... on PullRequest { number state }")

    today = datetime.date.today()
    rows = []
    for i in issues:
        mentioned = [(n, prs[n]["state"]) for n in refs[i["number"]] if n in prs and prs[n]["__typename"] == "PullRequest" and prs[n]["state"] != "CLOSED"]
        block, check = flags(i, a.repo, mentioned)
        status = "BLOCK" if block else "CHECK" if check else "-"
        filed_by = "maint" if i["authorAssociation"] in MAINT else "user"
        replied = any(c["authorAssociation"] in MAINT for c in i["comments"]["nodes"])
        good = any(GOOD_LABEL.search(l["name"]) for l in i["labels"]["nodes"])
        age = (today - datetime.date.fromisoformat(i["createdAt"][:10])).days
        rows.append(((["-", "CHECK", "BLOCK"].index(status), filed_by == "maint", not good, not replied, age),
                     [status, i["number"], age, filed_by, "yes" if replied else "no", i["comments"]["totalCount"],
                      i["reactions"]["totalCount"], ",".join(l["name"] for l in i["labels"]["nodes"]) or "-",
                      "; ".join(block + check) or "-", i["title"][:90]]))
    print("status\tnumber\tage_d\tfiled_by\tmaint_replied\tcomments\t+1\tlabels\tflags\ttitle")
    for _, row in sorted(rows, key=lambda r: r[0]):
        print("\t".join(map(str, row)))


if __name__ == "__main__":
    main()
