import os
import subprocess
import tempfile
import unittest
from git_archaeologist.core.excavator import Excavator
from git_archaeologist.exporters.html_report import generate_html_report
from git_archaeologist.exporters.markdown import generate_markdown_report
from git_archaeologist.exporters.json_export import generate_json_report


def run_cmd(args, cwd):
    res = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return res.stdout.strip()


class TestGitRepoE2E(unittest.TestCase):
    def setUp(self):
        self.tmpdir_obj = tempfile.TemporaryDirectory()
        self.tmpdir = self.tmpdir_obj.name

        # Initialize git repo
        run_cmd(["git", "init"], cwd=self.tmpdir)
        run_cmd(["git", "config", "user.name", "Tester"], cwd=self.tmpdir)
        run_cmd(["git", "config", "user.email", "tester@example.com"], cwd=self.tmpdir)

        # 1. Genesis commit: adds core function and a unit test to prevent race condition
        app_file = os.path.join(self.tmpdir, "network.py")
        test_file = os.path.join(self.tmpdir, "test_network.py")

        with open(app_file, "w", encoding="utf-8") as f:
            f.write(
                "# Network Module\n"
                "import time\n\n"
                "def connect():\n"
                "    # Safeguard against socket stall\n"
                "    time.sleep(0.15)\n"
                "    return True\n"
            )

        with open(test_file, "w", encoding="utf-8") as f:
            f.write(
                "def test_connect_stall():\n"
                "    assert True\n"
            )

        run_cmd(["git", "add", "network.py", "test_network.py"], cwd=self.tmpdir)
        run_cmd(["git", "commit", "-m", "fix(net): prevent TCP window stall under concurrency (fixes #1842)"], cwd=self.tmpdir)

        # 2. Churn commit: reformat / style (reindent time.sleep)
        with open(app_file, "w", encoding="utf-8") as f:
            f.write(
                "# Network Module\n"
                "import time\n\n"
                "def connect():\n"
                "    # Safeguard against socket stall\n"
                "      time.sleep(0.15)  \n"
                "    return True\n"
            )
        run_cmd(["git", "add", "network.py"], cwd=self.tmpdir)
        run_cmd(["git", "commit", "-m", "style: format code with black and reindent"], cwd=self.tmpdir)

        # 3. Surface commit: add a comment at the top
        with open(app_file, "w", encoding="utf-8") as f:
            f.write(
                "# Production Network Module v2\n"
                "import time\n\n"
                "def connect():\n"
                "    # Safeguard against socket stall\n"
                "      time.sleep(0.15)  \n"
                "    return True\n"
            )
        run_cmd(["git", "add", "network.py"], cwd=self.tmpdir)
        run_cmd(["git", "commit", "-m", "docs: update module description header"], cwd=self.tmpdir)

    def tearDown(self):
        self.tmpdir_obj.cleanup()

    def test_excavator_e2e(self):
        excavator = Excavator(repo_path=self.tmpdir)
        report = excavator.excavate("network.py:6-7")

        self.assertEqual(report.target.rel_path, "network.py")
        self.assertIn("time.sleep(0.15)", report.target.code_snippet)
        self.assertGreaterEqual(report.total_commits_traversed, 2)

        # Churn bypass verification
        self.assertGreaterEqual(report.churn_commits_bypassed, 1)

        # Genesis verification
        self.assertIn("fix(net): prevent TCP window stall", report.genesis_node.commit_meta.subject)
        self.assertIn("#1842", report.context.linked_issues)
        self.assertTrue(any("test_network.py" in t for t in report.context.co_changed_tests))

        # Exporters verification
        html = generate_html_report(report)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("time.sleep(0.15)", html)
        self.assertIn("#1842", html)

        md = generate_markdown_report(report)
        self.assertIn("## 🏛️ Git-Archaeologist Dossier", md)
        self.assertIn("fix(net): prevent TCP window stall", md)

        json_str = generate_json_report(report)
        self.assertIn('"level":', json_str)
        self.assertIn('"#1842"', json_str)


if __name__ == "__main__":
    unittest.main()
