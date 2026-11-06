---
name: git-archaeologist
description: Deep historical code excavation and Chesterton's Fence risk evaluator. Penetrates cosmetic formatting/churn commits to discover true genesis events, co-committed test suites, linked issue context, and architectural risk before refactoring or removing legacy code.
agent_created: true
---

# Git-Archaeologist (代码考古学长)

## 1. Overview & Core Mission
`git-archaeologist` is an archaeological engine for software repositories. It solves the classic engineering dilemma: **"Why was this weird line written? Is it safe to delete or refactor?"**

Standard `git blame` is shallow: it usually stops at the last linter, formatter, or file rename commit. `git-archaeologist` penetrates layers of cosmetic noise to locate:
1. **The True Genesis Event (起源提交)**: The exact commit where the business or defensive logic was born.
2. **Co-Committed Regression Tests (伴生测试套件)**: The specific tests created alongside this code that protect its subtle behavioral invariants.
3. **Traceable Issue Context**: Bug reports, PR discussions, Jira tickets, and CVE identifiers.
4. **Archaeological Risk Score (0-100)**: Evaluates whether code is a **Chesterton's Fence** (load-bearing wall) and outputs actionable verification steps.

---

## 2. When to Invoke
An agent should invoke `git-archaeologist` whenever:
- Planning to refactor, delete, or modify unfamiliar code that looks redundant or like an unnecessary workaround (e.g. `time.sleep`, retry loop, defensive `try/except: pass`, strange null checks).
- Answering user questions about "Why does this exist?" or "Who wrote this feature and what was the historical context?".
- Generating pull request explanations and risk assessments for legacy code changes.

---

## 3. CLI Usage

```bash
# Basic excavation of line or range
python -m git_archaeologist excavate path/to/file.py:42-50

# Generate standalone interactive HTML report
python -m git_archaeologist excavate path/to/file.py:42 --format html --output report.html

# Output JSON for automated agent ingestion
python -m git_archaeologist excavate path/to/file.py:42-60 --format json
```
