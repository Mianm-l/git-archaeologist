"""
Terminal Exporter for Git-Archaeologist.
Renders clean ANSI color-coded timelines and archaeological summaries.
"""

from __future__ import annotations
import sys
from git_archaeologist.core.excavator import ExcavationReport


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"
    BG_GREEN = "\033[42m"


def print_excavation_report(report: ExcavationReport, stream=sys.stdout):
    risk = report.risk
    target = report.target
    gen = report.genesis_node.commit_meta
    surf = report.surface_node.commit_meta

    # Risk badge
    if risk.level == "CRITICAL_LOAD_BEARING":
        badge = f"{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD} [CRITICAL CHESTERTON'S FENCE] {Colors.RESET}"
        score_color = Colors.RED
    elif risk.level == "HIGH":
        badge = f"{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD} [HIGH ARCHAEOLOGICAL RISK] {Colors.RESET}"
        score_color = Colors.RED
    elif risk.level == "MODERATE":
        badge = f"{Colors.BG_YELLOW}{Colors.WHITE}{Colors.BOLD} [MODERATE RISK] {Colors.RESET}"
        score_color = Colors.YELLOW
    else:
        badge = f"{Colors.BG_GREEN}{Colors.WHITE}{Colors.BOLD} [LOW RISK / REFACTORABLE] {Colors.RESET}"
        score_color = Colors.GREEN

    stream.write(f"\n{Colors.BOLD}{Colors.CYAN}╭─────────────────────────────────────────────────────────────╮{Colors.RESET}\n")
    stream.write(f"{Colors.BOLD}{Colors.CYAN}│  🏛️  GIT-ARCHAEOLOGIST EXCAVATION DOSSIER                     │{Colors.RESET}\n")
    stream.write(f"{Colors.BOLD}{Colors.CYAN}╰─────────────────────────────────────────────────────────────╯{Colors.RESET}\n")

    stream.write(f"\n{Colors.BOLD}📍 TARGET CODE LOCATION:{Colors.RESET} {target.rel_path}:{target.start_line}-{target.end_line}\n")
    stream.write(f"{Colors.DIM}---------------------------------------------------------------{Colors.RESET}\n")
    for idx, line in enumerate(target.code_snippet.splitlines(), start=target.start_line):
        stream.write(f"{Colors.CYAN}{idx:4d} |{Colors.RESET} {line}\n")
    stream.write(f"{Colors.DIM}---------------------------------------------------------------{Colors.RESET}\n")

    # Risk Gauge
    stream.write(f"\n{Colors.BOLD}📊 ARCHAEOLOGICAL RISK INDEX:{Colors.RESET} {badge} {score_color}{risk.total_score}/100{Colors.RESET}\n")
    stream.write(f"   {Colors.BOLD}Verdict:{Colors.RESET} {risk.recommendation}\n")

    # Risk Breakdown
    stream.write(f"\n{Colors.BOLD}🔍 RISK SCORE FACTORS:{Colors.RESET}\n")
    for f in risk.factors:
        stream.write(f"   • {Colors.BOLD}{f.name}:{Colors.RESET} {score_color}{f.score}/{f.max_score}{Colors.RESET} -> {f.description}\n")

    # Genesis vs Surface
    stream.write(f"\n{Colors.BOLD}🌱 TRUE GENESIS EVENT (创生提交):{Colors.RESET}\n")
    stream.write(f"   Commit:  {Colors.YELLOW}{gen.short_hash}{Colors.RESET} ({gen.hash})\n")
    stream.write(f"   Author:  {gen.author_name} <{gen.author_email}>\n")
    stream.write(f"   Date:    {gen.date_str}\n")
    stream.write(f"   Intent:  {Colors.BOLD}{report.context.intent}{Colors.RESET} (Confidence: {int(report.context.intent_confidence*100)}%)\n")
    stream.write(f"   Subject: {Colors.BOLD}{gen.subject}{Colors.RESET}\n")

    if report.context.linked_issues:
        stream.write(f"   Issues:  {Colors.CYAN}{', '.join(report.context.linked_issues)}{Colors.RESET}\n")
    if report.context.cves:
        stream.write(f"   CVEs:    {Colors.RED}{', '.join(report.context.cves)}{Colors.RESET}\n")

    # Guarding Tests
    if report.context.co_changed_tests:
        stream.write(f"\n{Colors.BOLD}🛡️  CO-COMMITTED REGRESSION TESTS ({len(report.context.co_changed_tests)}):{Colors.RESET}\n")
        for t in report.context.co_changed_tests:
            stream.write(f"   • {Colors.GREEN}{t}{Colors.RESET}\n")
    else:
        stream.write(f"\n{Colors.YELLOW}⚠️  No unit tests were co-committed with this code.{Colors.RESET}\n")

    # Action Items
    if risk.action_items:
        stream.write(f"\n{Colors.BOLD}📋 RECOMMENDED REFACTORING PROTOCOL:{Colors.RESET}\n")
        for item in risk.action_items:
            stream.write(f"   [ ] {item}\n")

    # Timeline Graph
    stream.write(f"\n{Colors.BOLD}📜 EVOLUTION TIMELINE ({len(report.timeline)} events, {report.churn_commits_bypassed} churn bypassed):{Colors.RESET}\n")
    for idx, node in enumerate(report.timeline):
        m = node.commit_meta
        is_last = (idx == len(report.timeline) - 1)
        prefix = "└──" if is_last else "├──"

        if node.role == "GENESIS":
            role_badge = f"{Colors.GREEN}[GENESIS]{Colors.RESET}"
        elif node.role == "SURFACE":
            role_badge = f"{Colors.CYAN}[SURFACE/HEAD]{Colors.RESET}"
        elif node.is_noise:
            role_badge = f"{Colors.DIM}[CHURN BYPASS: {node.noise_reason}]{Colors.RESET}"
        else:
            role_badge = f"{Colors.YELLOW}[MUTATION]{Colors.RESET}"

        stream.write(f"  {prefix} {Colors.BOLD}{m.short_hash}{Colors.RESET} {m.date_str[:10]} {role_badge} {m.author_name}: {m.subject}\n")

    stream.write("\n")
