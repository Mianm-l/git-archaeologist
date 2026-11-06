"""
Context Analyzer for Git-Archaeologist.
Extracts semantic intent, linked issues, PR references, and co-changed test files
from the commit that introduced or modified the code.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Dict, Set
from git_archaeologist.core.git_wrapper import CommitMeta


@dataclass
class ArchaeologicalContext:
    intent: str  # SECURITY, HOTFIX, BUGFIX, PERF, FEATURE, REFACTOR, CHORE, UNKNOWN
    intent_confidence: float  # 0.0 - 1.0
    linked_issues: List[str] = field(default_factory=list)
    linked_prs: List[str] = field(default_factory=list)
    cves: List[str] = field(default_factory=list)
    co_changed_tests: List[str] = field(default_factory=list)
    co_changed_docs: List[str] = field(default_factory=list)
    co_changed_configs: List[str] = field(default_factory=list)
    co_changed_modules: List[str] = field(default_factory=list)
    historical_notes: List[str] = field(default_factory=list)


class ContextAnalyzer:
    """Analyzes historical context, references, and co-changed files."""

    ISSUE_PATTERNS = [
        r"(?:(?:fixes|resolves|closes|refs|see)\s+)?#([0-9]+)\b",
        r"\b([A-Z]{2,10}-[0-9]+)\b",  # Jira pattern e.g. INFRA-1024, BUG-55
        r"\b(GH-[0-9]+)\b",
    ]

    CVE_PATTERN = r"\b(CVE-\d{4}-\d{4,7})\b"
    PR_PATTERN = r"\b(?:PR|pull\s+request|merged\s+pr)\s*#?([0-9]+)\b"

    TEST_FILE_PATTERNS = [
        re.compile(r"(^|/)(?:tests?|__tests__|spec)/", re.IGNORECASE),
        re.compile(r"(^|/)(?:test_[^/]+|[^/]+_test|[^/]+\.test|[^/]+\.spec|[^/]+Test)\.[a-zA-Z0-9]+$", re.IGNORECASE),
    ]

    DOC_FILE_PATTERNS = [
        re.compile(r"(^|/)(?:docs?|documentation)/", re.IGNORECASE),
        re.compile(r"\.(?:md|markdown|rst|txt|adoc)$", re.IGNORECASE),
    ]

    CONFIG_FILE_PATTERNS = [
        re.compile(r"\.(?:ya?ml|json|toml|ini|env|properties|xml)$", re.IGNORECASE),
        re.compile(r"(^|/)(?:Dockerfile|Makefile|docker-compose|k8s|helm)", re.IGNORECASE),
    ]

    def analyze(self, meta: CommitMeta) -> ArchaeologicalContext:
        full_text = f"{meta.subject}\n\n{meta.body}"

        # 1. Extract Issues & PRs
        issues: Set[str] = set()
        for p in self.ISSUE_PATTERNS:
            for match in re.finditer(p, full_text, re.IGNORECASE):
                if match.groups() and match.group(1):
                    val = match.group(1).strip()
                    if val.isdigit():
                        val = f"#{val}"
                else:
                    val = match.group(0).strip()
                issues.add(val)

        cves = list(set(re.findall(self.CVE_PATTERN, full_text, re.IGNORECASE)))
        prs = list(set(re.findall(self.PR_PATTERN, full_text, re.IGNORECASE)))

        # 2. Categorize Co-Changed Files
        tests: List[str] = []
        docs: List[str] = []
        configs: List[str] = []
        modules: List[str] = []

        for f in meta.changed_files:
            f_norm = f.replace("\\", "/")
            if any(p.search(f_norm) for p in self.TEST_FILE_PATTERNS):
                tests.append(f_norm)
            elif any(p.search(f_norm) for p in self.DOC_FILE_PATTERNS):
                docs.append(f_norm)
            elif any(p.search(f_norm) for p in self.CONFIG_FILE_PATTERNS):
                configs.append(f_norm)
            else:
                modules.append(f_norm)

        # 3. Determine Intent
        intent, conf = self._classify_intent(full_text, cves, tests)

        # 4. Generate Historical Notes
        notes: List[str] = []
        if cves:
            notes.append(f"Security fix associated with CVE: {', '.join(cves)}")
        if issues:
            notes.append(f"Explicitly traces back to tracking ticket/issue: {', '.join(sorted(issues))}")
        if tests:
            notes.append(f"Committed together with {len(tests)} test suite(s): {', '.join(tests[:3])}")
        else:
            notes.append("No dedicated unit/integration tests were committed in the genesis commit.")

        return ArchaeologicalContext(
            intent=intent,
            intent_confidence=conf,
            linked_issues=sorted(list(issues)),
            linked_prs=sorted(list(prs)),
            cves=cves,
            co_changed_tests=tests,
            co_changed_docs=docs,
            co_changed_configs=configs,
            co_changed_modules=modules,
            historical_notes=notes
        )

    def _classify_intent(self, text: str, cves: List[str], tests: List[str]) -> tuple[str, float]:
        text_lower = text.lower()

        if cves or any(k in text_lower for k in ["vulnerability", "exploit", "cve", "sanitize", "xss", "rce", "security patch"]):
            return "SECURITY", 0.95

        if any(text_lower.startswith(k) for k in ["hotfix", "urgent", "p0", "emergency"]) or "hotfix" in text_lower:
            return "HOTFIX", 0.90

        if any(k in text_lower for k in ["fix:", "fix(", "bug:", "bugfix", "fixes #", "resolves #", "regression", "workaround", "prevent crash", "race condition", "deadlock"]):
            return "BUGFIX", 0.85

        if any(k in text_lower for k in ["perf:", "perf(", "speedup", "latency", "benchmark", "optimize", "cache", "throughput"]):
            return "PERF", 0.85

        if any(k in text_lower for k in ["feat:", "feat(", "feature:", "implement", "add support", "new api"]):
            return "FEATURE", 0.80

        if any(k in text_lower for k in ["refactor:", "refactor(", "restructure", "clean up", "split"]):
            return "REFACTOR", 0.75

        if any(k in text_lower for k in ["chore:", "chore(", "deps:", "bump"]):
            return "CHORE", 0.70

        return "EVOLUTION", 0.50
