"""
JSON Exporter for Git-Archaeologist.
Serializes the full excavation report into structured JSON for CI and AI Agents.
"""

from __future__ import annotations
import json
from dataclasses import asdict
from git_archaeologist.core.excavator import ExcavationReport


def generate_json_report(report: ExcavationReport) -> str:
    data = {
        "target": asdict(report.target),
        "risk": {
            "total_score": report.risk.total_score,
            "level": report.risk.level,
            "headline": report.risk.headline,
            "recommendation": report.risk.recommendation,
            "factors": [asdict(f) for f in report.risk.factors],
            "action_items": report.risk.action_items,
        },
        "genesis": {
            "hash": report.genesis_node.commit_meta.hash,
            "short_hash": report.genesis_node.commit_meta.short_hash,
            "author": report.genesis_node.commit_meta.author_name,
            "date": report.genesis_node.commit_meta.date_str,
            "subject": report.genesis_node.commit_meta.subject,
            "intent": report.context.intent,
            "intent_confidence": report.context.intent_confidence,
            "linked_issues": report.context.linked_issues,
            "linked_prs": report.context.linked_prs,
            "cves": report.context.cves,
            "co_changed_tests": report.context.co_changed_tests,
            "co_changed_modules": report.context.co_changed_modules,
        },
        "surface": {
            "hash": report.surface_node.commit_meta.hash,
            "short_hash": report.surface_node.commit_meta.short_hash,
            "author": report.surface_node.commit_meta.author_name,
            "date": report.surface_node.commit_meta.date_str,
            "subject": report.surface_node.commit_meta.subject,
        },
        "timeline_summary": {
            "total_events": report.total_commits_traversed,
            "churn_bypassed": report.churn_commits_bypassed,
            "events": [
                {
                    "hash": n.commit_meta.short_hash,
                    "date": n.commit_meta.date_str,
                    "author": n.commit_meta.author_name,
                    "role": n.role,
                    "is_noise": n.is_noise,
                    "noise_reason": n.noise_reason,
                    "subject": n.commit_meta.subject,
                }
                for n in report.timeline
            ]
        }
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
