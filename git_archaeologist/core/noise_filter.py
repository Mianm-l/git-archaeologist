"""
Noise Filter for Git-Archaeologist.
Detects whether a commit touching the target lines is cosmetic noise,
code formatting, bulk refactoring, or a true functional mutation.
"""

from __future__ import annotations
import re
from typing import Tuple, List, Optional
from git_archaeologist.core.git_wrapper import CommitMeta


class NoiseFilter:
    """Classifies commits into True Mutations vs Cosmetic Noise."""

    # Heuristic keywords in commit subject/body indicating non-functional changes
    CHURN_SUBJECT_PATTERNS = [
        r"\b(format|reformat|prettier|black|autopep8|clang-format|rustfmt|gofmt)\b",
        r"\b(lint|eslint|flake8|pylint|rubocop|stylelint|checkstyle)\b",
        r"\b(cleanup|clean up|code clean|whitespace|trailing space|eol|indent|reindent)\b",
        r"\b(isort|sort imports|organize imports)\b",
        r"\b(license header|copyright update|update headers)\b",
        r"\b(typo in comment|fix comments|docstring typo)\b",
        r"^(style|chore\(style\)|chore\(format\)|chore\(lint\)|refactor\(format\)):",
    ]

    def __init__(self):
        self.compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.CHURN_SUBJECT_PATTERNS
        ]

    def is_noise_commit(
        self,
        meta: CommitMeta,
        diff_hunk: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Determines if a commit is cosmetic churn.
        Returns: (is_noise: bool, reason: str)
        """
        # 1. Check commit subject and body keywords
        text = f"{meta.subject}\n{meta.body}"
        for pattern in self.compiled_patterns:
            match = pattern.search(text)
            if match:
                return True, f"Subject matches cosmetic keyword: '{match.group(0)}'"

        # 2. Check if the diff hunk is purely whitespace / indentation
        if diff_hunk:
            is_ws, ws_reason = self.is_whitespace_only_diff(diff_hunk)
            if is_ws:
                return True, ws_reason

        # 3. Check for massive bulk touch (> 50 files changed with low diff per file)
        files_count = meta.stats.get("files_changed", len(meta.changed_files))
        if files_count >= 50:
            # Check if average insertion/deletion is small
            total_changes = meta.stats.get("insertions", 0) + meta.stats.get("deletions", 0)
            avg_per_file = total_changes / max(files_count, 1)
            if avg_per_file < 15:
                return True, f"Mass codebase touch ({files_count} files, avg {avg_per_file:.1f} lines/file)"

        return False, "Functional mutation"

    def is_whitespace_only_diff(self, diff_hunk: str) -> Tuple[bool, str]:
        """
        Checks if removed lines and added lines in the diff hunk differ only by whitespace.
        """
        lines = diff_hunk.splitlines()
        del_lines: List[str] = []
        add_lines: List[str] = []

        for line in lines:
            if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
                continue
            if line.startswith("-"):
                del_lines.append(line[1:])
            elif line.startswith("+"):
                add_lines.append(line[1:])

        if not del_lines and not add_lines:
            return False, ""

        # Normalize whitespace (strip all whitespace chars)
        del_normalized = "".join(re.sub(r"\s+", "", l) for l in del_lines)
        add_normalized = "".join(re.sub(r"\s+", "", l) for l in add_lines)

        if del_normalized == add_normalized and del_normalized != "":
            return True, "Diff changes are strictly whitespace or indentation adjustments"

        return False, ""
