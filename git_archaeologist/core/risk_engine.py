"""
Risk Engine for Git-Archaeologist.
Calculates the Archaeological Risk Index (0-100) and provides
refactoring/deletion recommendations based on Chesterton's Fence principle.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any
from git_archaeologist.core.git_wrapper import CommitMeta
from git_archaeologist.core.context_analyzer import ArchaeologicalContext


@dataclass
class RiskFactor:
    name: str
    score: int
    max_score: int
    description: str


@dataclass
class RiskEvaluation:
    total_score: int  # 0 to 100
    level: str  # LOW, MODERATE, HIGH, CRITICAL_LOAD_BEARING
    headline: str
    recommendation: str
    factors: List[RiskFactor] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)


class RiskEngine:
    """Calculates archaeological risk when modifying or deleting target code."""

    def evaluate(
        self,
        genesis_meta: CommitMeta,
        context: ArchaeologicalContext,
        total_mutations: int
    ) -> RiskEvaluation:
        factors: List[RiskFactor] = []
        now = datetime.now(timezone.utc)

        # Ensure genesis date has timezone or compare safely
        gen_date = genesis_meta.date
        if gen_date.tzinfo is None:
            now_dt = datetime.now()
            age_days = (now_dt - gen_date).days
        else:
            age_days = (now - gen_date).days

        # 1. Age Factor (0 - 30)
        # Chesterton's Fence: Old code that survived is often load-bearing
        if age_days > 365 * 3:
            age_score = 30
            age_desc = f"Untouched for >3 years ({age_days // 365} years). Classic Chesterton's Fence."
        elif age_days > 365:
            age_score = 22
            age_desc = f"Stable in production for {age_days // 30} months."
        elif age_days > 180:
            age_score = 12
            age_desc = f"Moderate age ({age_days // 30} months in production)."
        else:
            age_score = 5
            age_desc = f"Relatively recent code ({age_days} days old)."

        factors.append(RiskFactor("Code Age & Stability", age_score, 30, age_desc))

        # 2. Intent & Criticality Factor (0 - 35)
        intent_map = {
            "SECURITY": (35, "Introduced specifically as a security/vulnerability remedy."),
            "HOTFIX": (30, "Introduced under emergency hotfix conditions for production fire."),
            "BUGFIX": (24, "Introduced to resolve a known bug, edge-case, or race condition."),
            "PERF": (18, "Introduced to optimize latency, throughput, or memory leak."),
            "FEATURE": (10, "Standard business capability addition."),
            "REFACTOR": (6, "Code restructuring or architectural movement."),
            "CHORE": (4, "Maintenance or configuration chore."),
            "EVOLUTION": (8, "General evolutionary code addition.")
        }
        int_score, int_desc = intent_map.get(context.intent, (10, "Unknown initial intent."))
        factors.append(RiskFactor("Genesis Intent Criticality", int_score, 35, int_desc))

        # 3. Guarding Tests Factor (0 - 20)
        if context.co_changed_tests:
            test_score = 20
            test_desc = f"Guarded by {len(context.co_changed_tests)} co-committed regression test file(s)."
        else:
            test_score = 5
            test_desc = "No co-committed tests detected; behavioral invariants may be unverified."
        factors.append(RiskFactor("Regression Test Entanglement", test_score, 20, test_desc))

        # 4. Tracking Ticket / Issue Linkage (0 - 15)
        if context.cves:
            issue_score = 15
            issue_desc = f"Directly tied to CVE vulnerability reference: {', '.join(context.cves)}"
        elif context.linked_issues:
            issue_score = 12
            issue_desc = f"Linked to documented issue/ticket tracking: {', '.join(context.linked_issues[:2])}"
        else:
            issue_score = 3
            issue_desc = "No explicit issue, CVE, or ticket reference found."
        factors.append(RiskFactor("Traceable Issue / Incident Context", issue_score, 15, issue_desc))

        # Sum total
        total = sum(f.score for f in factors)
        total = min(100, max(0, total))

        # Action items & recommendations
        actions: List[str] = []
        if context.co_changed_tests:
            actions.append(f"Execute co-committed tests before and after changes: `{' '.join(context.co_changed_tests[:2])}`")
        if context.linked_issues:
            actions.append(f"Review historical discussion in {', '.join(context.linked_issues[:3])} to understand initial edge case")
        if context.intent in ("SECURITY", "HOTFIX"):
            actions.append("Conduct paired code review or security sign-off before modifying this block")
        actions.append("Ensure fallback or rollback strategy is defined in case subtle regression occurs")

        if total >= 80:
            level = "CRITICAL_LOAD_BEARING"
            headline = "CRITICAL LOAD-BEARING CODE (切斯特顿承重墙)"
            recommendation = "DO NOT TOUCH WITHOUT VERIFICATION. This code has historical bug/security roots and high stability. Removing it without reproducing original issues poses extreme regression danger."
        elif total >= 60:
            level = "HIGH"
            headline = "HIGH ARCHAEOLOGICAL RISK (高风险历史逻辑)"
            recommendation = "Proceed with caution. Carefully check linked test suites and issues to ensure the original edge-case or invariant is preserved."
        elif total >= 35:
            level = "MODERATE"
            headline = "MODERATE RISK (常规业务逻辑)"
            recommendation = "Standard refactoring risk. Ensure existing test coverage passes and downstream consumers are verified."
        else:
            level = "LOW"
            headline = "LOW RISK / SAFE TO REFACTOR (低风险可拆除)"
            recommendation = "Safe to modernize, simplify, or refactor. Recent or routine additions with minimal defensive entanglement."

        return RiskEvaluation(
            total_score=total,
            level=level,
            headline=headline,
            recommendation=recommendation,
            factors=factors,
            action_items=actions
        )
