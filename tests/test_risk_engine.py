import unittest
from datetime import datetime, timedelta, timezone
from git_archaeologist.core.git_wrapper import CommitMeta
from git_archaeologist.core.context_analyzer import ArchaeologicalContext
from git_archaeologist.core.risk_engine import RiskEngine


class TestRiskEngine(unittest.TestCase):
    def test_risk_engine_critical_fence(self):
        engine = RiskEngine()
        old_date = datetime.now(timezone.utc) - timedelta(days=365 * 4)
        meta = CommitMeta(
            hash="deadbeef",
            short_hash="deadbeef",
            author_name="Alice",
            author_email="alice@corp.com",
            date=old_date,
            date_str=old_date.isoformat(),
            subject="security: patch auth token bypass",
            body="Refs CVE-2022-1234"
        )

        ctx = ArchaeologicalContext(
            intent="SECURITY",
            intent_confidence=0.95,
            linked_issues=["#99"],
            cves=["CVE-2022-1234"],
            co_changed_tests=["tests/test_auth_bypass.py"]
        )

        eval_result = engine.evaluate(meta, ctx, total_mutations=3)
        self.assertGreaterEqual(eval_result.total_score, 80)
        self.assertEqual(eval_result.level, "CRITICAL_LOAD_BEARING")
        self.assertIn("DO NOT TOUCH WITHOUT VERIFICATION", eval_result.recommendation)
        self.assertTrue(any("tests/test_auth_bypass.py" in act for act in eval_result.action_items))

    def test_risk_engine_low_risk(self):
        engine = RiskEngine()
        recent_date = datetime.now(timezone.utc) - timedelta(days=10)
        meta = CommitMeta(
            hash="1234567",
            short_hash="1234567",
            author_name="Bob",
            author_email="bob@corp.com",
            date=recent_date,
            date_str=recent_date.isoformat(),
            subject="chore: bump minor dependency",
            body=""
        )

        ctx = ArchaeologicalContext(
            intent="CHORE",
            intent_confidence=0.70,
            linked_issues=[],
            cves=[],
            co_changed_tests=[]
        )

        eval_result = engine.evaluate(meta, ctx, total_mutations=1)
        self.assertLess(eval_result.total_score, 35)
        self.assertEqual(eval_result.level, "LOW")


if __name__ == "__main__":
    unittest.main()
