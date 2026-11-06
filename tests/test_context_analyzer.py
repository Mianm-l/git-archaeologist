import unittest
from datetime import datetime
from git_archaeologist.core.git_wrapper import CommitMeta
from git_archaeologist.core.context_analyzer import ContextAnalyzer


class TestContextAnalyzer(unittest.TestCase):
    def test_context_analyzer_issues_and_cve(self):
        analyzer = ContextAnalyzer()
        meta = CommitMeta(
            hash="abc1234",
            short_hash="abc1234",
            author_name="Security Eng",
            author_email="sec@corp.com",
            date=datetime.now(),
            date_str="2026-05-10",
            subject="fix: mitigate buffer overflow in parser (fixes #412)",
            body="Addresses CVE-2026-9999 and JIRA ticket PROJ-8812.",
            changed_files=[
                "src/parser.py",
                "tests/test_parser_cve.py",
                "docs/changelog.md"
            ]
        )

        ctx = analyzer.analyze(meta)
        self.assertEqual(ctx.intent, "SECURITY")
        self.assertIn("CVE-2026-9999", ctx.cves)
        self.assertTrue(any("#412" in i for i in ctx.linked_issues))
        self.assertTrue(any("PROJ-8812" in i for i in ctx.linked_issues))
        self.assertIn("tests/test_parser_cve.py", ctx.co_changed_tests)
        self.assertIn("docs/changelog.md", ctx.co_changed_docs)


if __name__ == "__main__":
    unittest.main()
