"""
Excavator for Git-Archaeologist.
The core engine that coordinates git history excavation, churn bypass,
and synthesis into an archaeological report.
"""

from __future__ import annotations
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from git_archaeologist.core.git_wrapper import (
    GitWrapper, CommitMeta, LineEvolutionStep, GitExecutionError
)
from git_archaeologist.core.noise_filter import NoiseFilter
from git_archaeologist.core.context_analyzer import ContextAnalyzer, ArchaeologicalContext
from git_archaeologist.core.risk_engine import RiskEngine, RiskEvaluation


@dataclass
class ExcavationNode:
    commit_meta: CommitMeta
    is_noise: bool
    noise_reason: str
    diff_hunk: str
    role: str  # "GENESIS", "MUTATION", "CHURN_FILTERED", "SURFACE"


@dataclass
class TargetSpecification:
    raw_target: str
    file_path: str
    rel_path: str
    start_line: int
    end_line: int
    code_snippet: str


@dataclass
class ExcavationReport:
    target: TargetSpecification
    genesis_node: ExcavationNode
    surface_node: ExcavationNode
    timeline: List[ExcavationNode]
    context: ArchaeologicalContext
    risk: RiskEvaluation
    total_commits_traversed: int
    churn_commits_bypassed: int


class Excavator:
    def __init__(self, repo_path: Optional[str] = None):
        self.git = GitWrapper(repo_path)
        self.noise_filter = NoiseFilter()
        self.context_analyzer = ContextAnalyzer()
        self.risk_engine = RiskEngine()

    def parse_target(self, target_str: str) -> Tuple[str, int, int]:
        """
        Parses 'path/to/file.ext:10-20' or 'path/to/file.ext:10' or 'path/to/file.ext'.
        """
        match = re.match(r"^(.+?)(?::(\d+)(?:-(\d+))?)?$", target_str)
        if not match:
            raise ValueError(f"Invalid target format: '{target_str}'. Expected 'file[:start[-end]]'")

        file_p = match.group(1).strip()
        start_str = match.group(2)
        end_str = match.group(3)

        abs_file = os.path.join(self.git.root_path, file_p) if not os.path.isabs(file_p) else file_p
        if not os.path.exists(abs_file):
            raise FileNotFoundError(f"File not found: '{abs_file}'")

        with open(abs_file, "r", encoding="utf-8", errors="replace") as f:
            total_lines = len(f.readlines())

        if total_lines == 0:
            raise ValueError(f"Target file '{file_p}' is empty.")

        if start_str is None:
            # Default to full file if line range not specified
            start_l = 1
            end_l = total_lines
        else:
            start_l = int(start_str)
            end_l = int(end_str) if end_str else start_l

        start_l = max(1, min(start_l, total_lines))
        end_l = max(start_l, min(end_l, total_lines))

        return abs_file, start_l, end_l

    def excavate(self, target_str: str, bypass_churn: bool = True) -> ExcavationReport:
        abs_file, start_l, end_l = self.parse_target(target_str)
        rel_path = self.git.get_relative_path(abs_file)

        # Extract code snippet currently in place
        with open(abs_file, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        snippet = "".join(all_lines[start_l - 1:end_l])

        target_spec = TargetSpecification(
            raw_target=target_str,
            file_path=abs_file,
            rel_path=rel_path,
            start_line=start_l,
            end_line=end_l,
            code_snippet=snippet
        )

        # Trace history via git log -L
        line_steps = self.git.get_line_log(abs_file, start_l, end_l)
        if not line_steps:
            # Fallback to blame
            blame_info = self.git.get_blame_line(abs_file, start_l)
            if blame_info:
                meta = self.git.get_commit_meta(blame_info["hash"])
                diff = self.git.get_commit_diff(meta.hash, abs_file)
                line_steps = [LineEvolutionStep(
                    commit_hash=meta.hash,
                    author=meta.author_name,
                    date=meta.date_str,
                    subject=meta.subject,
                    diff_hunk=diff
                )]
            else:
                raise GitExecutionError(f"Unable to retrieve history for '{rel_path}:{start_l}-{end_l}'.")

        # Build timeline nodes
        timeline: List[ExcavationNode] = []
        churn_count = 0

        for idx, step in enumerate(line_steps):
            try:
                meta = self.git.get_commit_meta(step.commit_hash)
            except Exception:
                # If meta fetch fails, build partial meta
                meta = CommitMeta(
                    hash=step.commit_hash,
                    short_hash=step.commit_hash[:7],
                    author_name=step.author,
                    author_email="",
                    date=None,  # type: ignore
                    date_str=step.date,
                    subject=step.subject
                )

            is_noise, noise_reason = self.noise_filter.is_noise_commit(meta, step.diff_hunk)
            if is_noise:
                churn_count += 1

            # Role assignment
            if idx == 0:
                role = "SURFACE"
            elif idx == len(line_steps) - 1:
                role = "GENESIS"
            elif is_noise:
                role = "CHURN_FILTERED"
            else:
                role = "MUTATION"

            node = ExcavationNode(
                commit_meta=meta,
                is_noise=is_noise,
                noise_reason=noise_reason,
                diff_hunk=step.diff_hunk,
                role=role
            )
            timeline.append(node)

        # Surface is timeline[0] (most recent commit modifying this line)
        surface_node = timeline[0]

        # Genesis candidate
        # If bypass_churn is enabled, work backwards from the oldest commit,
        # but if the oldest commit itself is the origin of the line, that's GENESIS.
        genesis_node = timeline[-1]
        genesis_node.role = "GENESIS"

        # Analyze context of the true genesis
        context = self.context_analyzer.analyze(genesis_node.commit_meta)

        # Evaluate archaeological risk
        risk = self.risk_engine.evaluate(
            genesis_meta=genesis_node.commit_meta,
            context=context,
            total_mutations=len([n for n in timeline if not n.is_noise])
        )

        return ExcavationReport(
            target=target_spec,
            genesis_node=genesis_node,
            surface_node=surface_node,
            timeline=timeline,
            context=context,
            risk=risk,
            total_commits_traversed=len(timeline),
            churn_commits_bypassed=churn_count
        )
