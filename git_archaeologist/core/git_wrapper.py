"""
Git Wrapper for Git-Archaeologist.
Executes git commands safely and parses line-level histories.
"""

from __future__ import annotations
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


class GitExecutionError(Exception):
    """Raised when a git command fails."""
    pass


@dataclass
class CommitMeta:
    hash: str
    short_hash: str
    author_name: str
    author_email: str
    date: datetime
    date_str: str
    subject: str
    body: str = ""
    changed_files: List[str] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)  # insertions, deletions, files_changed


@dataclass
class LineEvolutionStep:
    commit_hash: str
    author: str
    date: str
    subject: str
    diff_hunk: str
    lines: List[str] = field(default_factory=list)


class GitWrapper:
    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = os.path.abspath(repo_path) if repo_path else None
        if self.repo_path:
            self.root_path = self._find_repo_root(self.repo_path)
        else:
            self.root_path = self._try_find_repo_root(os.getcwd())

    def _try_find_repo_root(self, start_path: str) -> Optional[str]:
        try:
            return self._find_repo_root(start_path)
        except GitExecutionError:
            return None

    def ensure_repo(self, hint_path: Optional[str] = None) -> str:
        if self.root_path and os.path.exists(self.root_path):
            return self.root_path
        if hint_path:
            self.root_path = self._find_repo_root(hint_path)
            self.repo_path = self.root_path
            return self.root_path
        raise GitExecutionError("No git repository found in current working directory.")

    def _find_repo_root(self, start_path: str) -> str:
        """Finds the root directory containing the .git directory."""
        cur = start_path
        if os.path.isfile(cur):
            cur = os.path.dirname(cur)
        while cur:
            if os.path.exists(os.path.join(cur, ".git")):
                return cur
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
        raise GitExecutionError(f"No git repository found in '{start_path}' or any of its parents.")

    def run_git(self, args: List[str], cwd: Optional[str] = None) -> str:
        """Runs a git command with UTF-8 fallback decoding."""
        working_dir = cwd or self.root_path
        cmd = ["git"] + args
        try:
            res = subprocess.run(
                cmd,
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                check=False
            )
        except FileNotFoundError:
            raise GitExecutionError("Git executable not found in PATH.")

        if res.returncode != 0:
            err_msg = self._decode_bytes(res.stderr).strip()
            raise GitExecutionError(f"Git command failed ({' '.join(cmd)}): {err_msg}")

        return self._decode_bytes(res.stdout)

    def _decode_bytes(self, b: bytes) -> str:
        for enc in ("utf-8", "gbk", "latin-1"):
            try:
                return b.decode(enc)
            except UnicodeDecodeError:
                continue
        return b.decode("utf-8", errors="replace")

    def get_relative_path(self, file_path: str) -> str:
        """Converts an absolute or relative path to repo-relative path using forward slashes."""
        abs_p = os.path.abspath(file_path if os.path.isabs(file_path) else os.path.join(self.repo_path, file_path))
        rel_p = os.path.relpath(abs_p, self.root_path)
        return rel_p.replace("\\", "/")

    def get_commit_meta(self, commit_hash: str) -> CommitMeta:
        """Fetches structured metadata and changed files for a commit."""
        # %H=hash, %h=short, %an=author name, %ae=author email, %aI=ISO8601 date, %s=subject, %b=body
        sep = "----ARCH_SEP----"
        fmt = f"%H{sep}%h{sep}%an{sep}%ae{sep}%aI{sep}%s{sep}%b"
        raw = self.run_git(["show", "-s", f"--format={fmt}", commit_hash])
        parts = raw.split(sep)
        if len(parts) < 7:
            # Fallback if body formatting split fails
            parts += [""] * (7 - len(parts))

        c_hash = parts[0].strip()
        s_hash = parts[1].strip()
        an = parts[2].strip()
        ae = parts[3].strip()
        d_str = parts[4].strip()
        subject = parts[5].strip()
        body = parts[6].strip()

        try:
            dt = datetime.fromisoformat(d_str)
        except Exception:
            dt = datetime.now()

        # Fetch changed files and stats
        name_status = self.run_git(["show", "--numstat", "--format=", commit_hash]).strip().splitlines()
        changed_files: List[str] = []
        insertions = 0
        deletions = 0

        for line in name_status:
            line = line.strip()
            if not line:
                continue
            cols = line.split("\t")
            if len(cols) >= 3:
                ins, dels, fn = cols[0], cols[1], cols[2]
                if ins.isdigit():
                    insertions += int(ins)
                if dels.isdigit():
                    deletions += int(dels)
                changed_files.append(fn.strip())

        return CommitMeta(
            hash=c_hash,
            short_hash=s_hash,
            author_name=an,
            author_email=ae,
            date=dt,
            date_str=d_str,
            subject=subject,
            body=body,
            changed_files=changed_files,
            stats={
                "insertions": insertions,
                "deletions": deletions,
                "files_changed": len(changed_files)
            }
        )

    def get_commit_diff(self, commit_hash: str, file_path: Optional[str] = None) -> str:
        """Returns unified diff for the commit (optionally restricted to a file)."""
        args = ["show", "--format=", "-p", commit_hash]
        if file_path:
            rel = self.get_relative_path(file_path)
            args += ["--", rel]
        return self.run_git(args)

    def get_line_log(self, file_path: str, start_line: int, end_line: int) -> List[LineEvolutionStep]:
        """
        Executes git log -L <start>,<end>:<file> to trace line evolution.
        Returns steps in reverse chronological order (newest first).
        """
        rel = self.get_relative_path(file_path)
        # Using git log -L
        args = ["log", f"-L{start_line},{end_line}:{rel}"]
        raw = self.run_git(args)

        steps: List[LineEvolutionStep] = []
        # Parse commits from git log -L
        # Each commit starts with 'commit <hash>'
        commit_chunks = re.split(r"(?m)^commit ([0-9a-fA-F]{40})", raw)
        if len(commit_chunks) <= 1:
            return steps

        # Chunks will be [header_or_empty, hash1, body1, hash2, body2, ...]
        idx = 1
        while idx < len(commit_chunks):
            c_hash = commit_chunks[idx].strip()
            c_body = commit_chunks[idx + 1] if idx + 1 < len(commit_chunks) else ""
            idx += 2

            author = ""
            date_str = ""
            subject = ""
            lines = c_body.splitlines()
            body_start = 0

            for i, line in enumerate(lines):
                if line.startswith("Author:"):
                    author = line[7:].strip()
                elif line.startswith("Date:"):
                    date_str = line[5:].strip()
                elif line.startswith("    ") and not subject:
                    subject = line.strip()
                elif line.startswith("diff --git"):
                    body_start = i
                    break

            diff_part = "\n".join(lines[body_start:]) if body_start > 0 else ""
            steps.append(LineEvolutionStep(
                commit_hash=c_hash,
                author=author,
                date=date_str,
                subject=subject,
                diff_hunk=diff_part
            ))

        return steps

    def get_blame_line(self, file_path: str, line_no: int) -> Optional[Dict[str, Any]]:
        """Runs git blame on a specific line to get its immediate commit hash and metadata."""
        rel = self.get_relative_path(file_path)
        args = ["blame", "-p", f"-L{line_no},{line_no}", "--", rel]
        try:
            raw = self.run_git(args)
        except GitExecutionError:
            return None

        lines = raw.splitlines()
        if not lines:
            return None

        first_line = lines[0].split()
        commit_hash = first_line[0]

        meta: Dict[str, Any] = {"hash": commit_hash}
        for line in lines[1:]:
            if line.startswith("author "):
                meta["author"] = line[7:].strip()
            elif line.startswith("author-time "):
                meta["time"] = int(line[12:].strip())
            elif line.startswith("summary "):
                meta["summary"] = line[8:].strip()

        return meta
