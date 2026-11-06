import unittest
from datetime import datetime
from git_archaeologist.core.git_wrapper import CommitMeta
from git_archaeologist.core.noise_filter import NoiseFilter


class TestNoiseFilter(unittest.TestCase):
    def test_noise_filter_by_message(self):
        nf = NoiseFilter()

        # Cosmetic commit
        c1 = CommitMeta(
            hash="1111111", short_hash="1111111", author_name="Dev", author_email="dev@example.com",
            date=datetime.now(), date_str="2026-01-01", subject="style: run black and prettier", body=""
        )
        is_noise, reason = nf.is_noise_commit(c1)
        self.assertTrue(is_noise)
        self.assertTrue("black" in reason or "prettier" in reason or "Subject matches" in reason)

        # Functional commit
        c2 = CommitMeta(
            hash="2222222", short_hash="2222222", author_name="Dev", author_email="dev@example.com",
            date=datetime.now(), date_str="2026-01-01", subject="fix: handle timeout on socket close #123", body=""
        )
        is_noise, _ = nf.is_noise_commit(c2)
        self.assertFalse(is_noise)

    def test_noise_filter_by_whitespace_diff(self):
        nf = NoiseFilter()
        diff = """
--- a/file.py
+++ b/file.py
@@ -10,3 +10,3 @@
-    def foo():
-        pass
+  def foo():
+    pass
"""
        c = CommitMeta(
            hash="3333333", short_hash="3333333", author_name="Dev", author_email="dev@example.com",
            date=datetime.now(), date_str="2026-01-01", subject="update indentation", body=""
        )
        is_noise, reason = nf.is_noise_commit(c, diff_hunk=diff)
        self.assertTrue(is_noise)
        self.assertTrue("whitespace" in reason.lower() or "indentation" in reason.lower())


if __name__ == "__main__":
    unittest.main()
