"""
HTML Report Exporter for Git-Archaeologist.
Generates a zero-dependency, ultra-sleek dark-mode interactive HTML report.
"""

from __future__ import annotations
import html
from git_archaeologist.core.excavator import ExcavationReport


def generate_html_report(report: ExcavationReport) -> str:
    target = report.target
    risk = report.risk
    gen = report.genesis_node.commit_meta
    ctx = report.context

    # Risk badge and gauge color
    if risk.level == "CRITICAL_LOAD_BEARING":
        risk_color = "#ef4444"
        risk_label = "CRITICAL LOAD-BEARING"
        gauge_stroke = "#ef4444"
    elif risk.level == "HIGH":
        risk_color = "#f97316"
        risk_label = "HIGH ARCHAEOLOGICAL RISK"
        gauge_stroke = "#f97316"
    elif risk.level == "MODERATE":
        risk_color = "#eab308"
        risk_label = "MODERATE RISK"
        gauge_stroke = "#eab308"
    else:
        risk_color = "#22c55e"
        risk_label = "LOW RISK / SAFE TO REFACTOR"
        gauge_stroke = "#22c55e"

    dash_offset = int(283 * (1 - (risk.total_score / 100.0)))

    # Code lines
    code_lines_html = []
    for idx, l in enumerate(target.code_snippet.splitlines(), start=target.start_line):
        code_lines_html.append(
            f'<div class="code-line"><span class="line-no">{idx:4d}</span><span class="line-text">{html.escape(l)}</span></div>'
        )
    code_block = "\n".join(code_lines_html)

    # Risk factors list
    factors_html = []
    for f in risk.factors:
        pct = int((f.score / max(f.max_score, 1)) * 100)
        factors_html.append(f"""
        <div class="factor-row">
            <div class="factor-header">
                <span class="factor-name">{html.escape(f.name)}</span>
                <span class="factor-score">{f.score} / {f.max_score}</span>
            </div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: {pct}%; background-color: {risk_color};"></div>
            </div>
            <div class="factor-desc">{html.escape(f.description)}</div>
        </div>
        """)
    factors_block = "\n".join(factors_html)

    # Action items list
    actions_html = []
    for act in risk.action_items:
        actions_html.append(f'<li><span class="check-box">✔</span> {html.escape(act)}</li>')
    actions_block = "\n".join(actions_html)

    # Timeline cards
    timeline_cards_html = []
    for idx, node in enumerate(report.timeline):
        m = node.commit_meta
        if node.role == "GENESIS":
            role_badge = '<span class="badge badge-genesis">🌱 GENESIS EVENT</span>'
        elif node.role == "SURFACE":
            role_badge = '<span class="badge badge-surface">📍 HEAD / SURFACE</span>'
        elif node.is_noise:
            role_badge = f'<span class="badge badge-churn">🧹 NOISE BYPASS: {html.escape(node.noise_reason)}</span>'
        else:
            role_badge = '<span class="badge badge-mutation">⚡ MUTATION</span>'

        diff_snippet = html.escape(node.diff_hunk[:2000]) if node.diff_hunk else "No diff hunk recorded."
        diff_id = f"diff-{idx}"

        timeline_cards_html.append(f"""
        <div class="timeline-item {'timeline-genesis' if node.role == 'GENESIS' else ''}">
            <div class="timeline-dot"></div>
            <div class="timeline-card">
                <div class="card-header">
                    <div class="card-title">
                        <span class="commit-hash">{m.short_hash}</span>
                        {role_badge}
                        <span class="commit-subject">{html.escape(m.subject)}</span>
                    </div>
                    <div class="card-meta">
                        <span>👤 {html.escape(m.author_name)}</span>
                        <span>📅 {html.escape(m.date_str[:10])}</span>
                        <button class="toggle-btn" onclick="toggleDiff('{diff_id}')">Toggle Diff</button>
                    </div>
                </div>
                <div id="{diff_id}" class="card-diff" style="display: {'block' if node.role == 'GENESIS' else 'none'};">
                    <pre><code>{diff_snippet}</code></pre>
                </div>
            </div>
        </div>
        """)
    timeline_block = "\n".join(timeline_cards_html)

    # Tests list
    if ctx.co_changed_tests:
        tests_items = "".join(f'<li class="test-item">🧪 <code>{html.escape(t)}</code></li>' for t in ctx.co_changed_tests)
        tests_block = f'<ul class="test-list">{tests_items}</ul>'
    else:
        tests_block = '<p class="warning-text">⚠️ No unit tests were co-committed in the genesis commit. Invariants might be implicit.</p>'

    template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Git-Archaeologist Dossier: {html.escape(target.rel_path)}</title>
    <style>
        :root {{
            --bg-color: #0d1117;
            --surface-color: #161b22;
            --surface-card: #21262d;
            --border-color: #30363d;
            --text-main: #f0f6fc;
            --text-muted: #8b949e;
            --accent-cyan: #38bdf8;
            --accent-blue: #3b82f6;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: var(--font-sans);
            padding: 30px 20px;
            line-height: 1.6;
        }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 30px;
        }}
        .logo-title {{ display: flex; align-items: center; gap: 14px; }}
        .logo-icon {{
            font-size: 32px;
            background: rgba(56, 189, 248, 0.1);
            padding: 10px 14px;
            border-radius: 12px;
            border: 1px solid rgba(56, 189, 248, 0.3);
        }}
        h1 {{ font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }}
        .target-sub {{ color: var(--text-muted); font-size: 14px; font-family: var(--font-mono); margin-top: 4px; }}
        
        /* Grid Layout */
        .dashboard-grid {{
            display: grid;
            grid-template-columns: 360px 1fr;
            gap: 24px;
            margin-bottom: 30px;
        }}
        @media (max-width: 860px) {{
            .dashboard-grid {{ grid-template-columns: 1fr; }}
        }}

        .panel {{
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
        }}
        .panel h2 {{
            font-size: 16px;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--text-muted);
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        /* Risk Gauge */
        .gauge-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 10px 0 20px 0;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 20px;
        }}
        .circular-chart {{ width: 140px; height: 140px; transform: rotate(-90deg); }}
        .circle-bg {{ fill: none; stroke: var(--border-color); stroke-width: 3.8; }}
        .circle {{
            fill: none;
            stroke-width: 3.8;
            stroke-linecap: round;
            stroke-dasharray: 283;
            stroke-dashoffset: {dash_offset};
            transition: stroke-dashoffset 1s ease-in-out;
        }}
        .gauge-score {{
            position: absolute;
            font-size: 32px;
            font-weight: 800;
            color: var(--text-main);
            font-family: var(--font-mono);
        }}
        .gauge-wrapper {{
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .risk-badge {{
            display: inline-block;
            margin-top: 14px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.5px;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid {risk_color};
            color: {risk_color};
        }}
        .recommendation-box {{
            margin-top: 14px;
            font-size: 13px;
            color: var(--text-main);
            line-height: 1.5;
            background: rgba(0, 0, 0, 0.3);
            padding: 12px;
            border-radius: 8px;
            border-left: 3px solid {risk_color};
        }}

        /* Factor Rows */
        .factor-row {{ margin-bottom: 14px; }}
        .factor-header {{ display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px; }}
        .factor-name {{ font-weight: 600; }}
        .factor-score {{ color: var(--text-muted); font-family: var(--font-mono); }}
        .progress-bar-bg {{ background: var(--border-color); height: 6px; border-radius: 3px; overflow: hidden; }}
        .progress-bar-fill {{ height: 100%; border-radius: 3px; }}
        .factor-desc {{ font-size: 11px; color: var(--text-muted); margin-top: 4px; }}

        /* Code Block */
        .code-container {{
            background: #090d13;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
            font-family: var(--font-mono);
            font-size: 13px;
            overflow-x: auto;
            margin-bottom: 20px;
        }}
        .code-line {{ display: flex; gap: 14px; }}
        .line-no {{ color: var(--text-muted); user-select: none; width: 40px; text-align: right; }}
        .line-text {{ color: #e6edf3; white-space: pre; }}

        /* Genesis Summary */
        .genesis-card {{
            background: rgba(56, 189, 248, 0.04);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
        }}
        .genesis-title {{ font-weight: 700; color: var(--accent-cyan); margin-bottom: 8px; display: flex; gap: 8px; align-items: center; }}
        .meta-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; font-size: 13px; margin-top: 10px; }}
        .meta-item span {{ color: var(--text-muted); display: block; font-size: 11px; }}
        .meta-item strong {{ color: var(--text-main); font-family: var(--font-mono); font-size: 13px; }}

        /* Action Checklist */
        .action-list {{ list-style: none; margin-top: 10px; }}
        .action-list li {{
            font-size: 13px;
            padding: 8px 12px;
            background: var(--surface-card);
            border-radius: 6px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .check-box {{ color: var(--accent-cyan); font-weight: bold; }}

        /* Tests List */
        .test-list {{ list-style: none; }}
        .test-item {{ font-size: 13px; margin-bottom: 6px; color: #4ade80; }}
        .test-item code {{ background: rgba(74, 222, 128, 0.1); padding: 2px 6px; border-radius: 4px; }}
        .warning-text {{ font-size: 13px; color: #facc15; }}

        /* Timeline */
        .timeline-section {{ margin-top: 30px; }}
        .timeline-wrapper {{ position: relative; padding-left: 28px; margin-top: 20px; }}
        .timeline-wrapper::before {{
            content: '';
            position: absolute;
            left: 8px;
            top: 10px;
            bottom: 10px;
            width: 2px;
            background: var(--border-color);
        }}
        .timeline-item {{ position: relative; margin-bottom: 20px; }}
        .timeline-dot {{
            position: absolute;
            left: -24px;
            top: 14px;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--accent-cyan);
            border: 2px solid var(--bg-color);
        }}
        .timeline-genesis .timeline-dot {{ background: #22c55e; width: 14px; height: 14px; left: -26px; }}
        .timeline-card {{
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 14px 18px;
        }}
        .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }}
        .commit-hash {{ font-family: var(--font-mono); font-weight: 700; color: #f59e0b; background: rgba(245, 158, 11, 0.1); padding: 2px 6px; border-radius: 4px; }}
        .commit-subject {{ font-weight: 600; margin-left: 6px; }}
        .card-meta {{ font-size: 12px; color: var(--text-muted); display: flex; gap: 14px; align-items: center; margin-top: 4px; }}
        .badge {{
            display: inline-block;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 12px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .badge-genesis {{ background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }}
        .badge-surface {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }}
        .badge-churn {{ background: rgba(139, 148, 158, 0.15); color: #8b949e; border: 1px solid rgba(139, 148, 158, 0.3); }}
        .badge-mutation {{ background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); }}
        .toggle-btn {{
            background: var(--surface-card);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            cursor: pointer;
        }}
        .toggle-btn:hover {{ background: var(--border-color); }}
        .card-diff {{
            margin-top: 12px;
            background: #090d13;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 10px;
            font-family: var(--font-mono);
            font-size: 11px;
            overflow-x: auto;
            max-height: 300px;
        }}
        footer {{
            margin-top: 50px;
            text-align: center;
            color: var(--text-muted);
            font-size: 12px;
            border-top: 1px solid var(--border-color);
            padding-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-title">
                <div class="logo-icon">🏛️</div>
                <div>
                    <h1>Git-Archaeologist Dossier</h1>
                    <div class="target-sub">{html.escape(target.rel_path)} : lines {target.start_line}-{target.end_line}</div>
                </div>
            </div>
            <div>
                <span class="risk-badge">{risk_label}</span>
            </div>
        </header>

        <div class="dashboard-grid">
            <!-- Left: Risk Evaluation -->
            <div class="panel">
                <h2>📊 Archaeological Risk</h2>
                <div class="gauge-container">
                    <div class="gauge-wrapper">
                        <svg viewBox="0 0 100 100" class="circular-chart">
                            <path class="circle-bg" d="M 50,50 m 0,-45 a 45,45 0 1 1 0,90 a 45,45 0 1 1 0,-90"/>
                            <path class="circle" stroke="{gauge_stroke}" d="M 50,50 m 0,-45 a 45,45 0 1 1 0,90 a 45,45 0 1 1 0,-90"/>
                        </svg>
                        <div class="gauge-score">{risk.total_score}</div>
                    </div>
                    <div class="recommendation-box">
                        <strong>Protocol Recommendation:</strong><br>
                        {html.escape(risk.recommendation)}
                    </div>
                </div>

                <h2>🔍 Risk Factors</h2>
                {factors_block}

                <h2 style="margin-top: 24px;">📋 Safe Refactoring Protocol</h2>
                <ul class="action-list">
                    {actions_block}
                </ul>
            </div>

            <!-- Right: Code & Genesis Context -->
            <div>
                <div class="panel" style="margin-bottom: 24px;">
                    <h2>📍 Target Code Segment</h2>
                    <div class="code-container">
                        {code_block}
                    </div>

                    <h2>🌱 Genesis Event Context</h2>
                    <div class="genesis-card">
                        <div class="genesis-title">
                            <span>🌱 Introduced in {gen.short_hash}</span>
                            <span class="badge badge-genesis">{ctx.intent}</span>
                        </div>
                        <p style="font-size: 14px; font-weight: 600; margin-bottom: 8px;">{html.escape(gen.subject)}</p>
                        <div class="meta-grid">
                            <div class="meta-item"><span>Original Author</span><strong>{html.escape(gen.author_name)}</strong></div>
                            <div class="meta-item"><span>Genesis Date</span><strong>{html.escape(gen.date_str[:10])}</strong></div>
                            <div class="meta-item"><span>Associated Tickets</span><strong>{html.escape(", ".join(ctx.linked_issues) or "None")}</strong></div>
                            <div class="meta-item"><span>CVE Reference</span><strong>{html.escape(", ".join(ctx.cves) or "None")}</strong></div>
                        </div>
                    </div>

                    <h2>🛡️ Co-Committed Regression Tests</h2>
                    {tests_block}
                </div>
            </div>
        </div>

        <!-- Full Evolution Timeline -->
        <div class="panel timeline-section">
            <h2>📜 Evolution Timeline & Churn Bypass ({len(report.timeline)} total events, {report.churn_commits_bypassed} churn bypassed)</h2>
            <div class="timeline-wrapper">
                {timeline_block}
            </div>
        </div>

        <footer>
            Generated by <strong>Git-Archaeologist</strong> &bull; Non-destructive Git Archaeology Engine &bull; Chesterton's Fence Guard
        </footer>
    </div>

    <script>
        function toggleDiff(id) {{
            const el = document.getElementById(id);
            if (!el) return;
            el.style.display = (el.style.display === 'none' || el.style.display === '') ? 'block' : 'none';
        }}
    </script>
</body>
</html>
"""
    return template
