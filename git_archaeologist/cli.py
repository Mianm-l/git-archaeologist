"""
Command Line Interface for Git-Archaeologist.
"""

from __future__ import annotations
import argparse
import sys
import os
from git_archaeologist import __version__
from git_archaeologist.core.excavator import Excavator
from git_archaeologist.core.git_wrapper import GitExecutionError
from git_archaeologist.exporters.terminal import print_excavation_report
from git_archaeologist.exporters.html_report import generate_html_report
from git_archaeologist.exporters.markdown import generate_markdown_report
from git_archaeologist.exporters.json_export import generate_json_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="git-archaeologist",
        description="🏛️ Git-Archaeologist: Find out WHY a line of code exists before you touch it."
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"Git-Archaeologist v{__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # excavate command
    excavate_parser = subparsers.add_parser(
        "excavate",
        help="Excavate the origin and evolution of a target file or line range"
    )
    excavate_parser.add_argument(
        "target",
        help="Target specification: 'path/to/file.py:start[-end]' or 'path/to/file.py'"
    )
    excavate_parser.add_argument(
        "--format", "-f",
        choices=["terminal", "html", "md", "json"],
        default="terminal",
        help="Output format (default: terminal)"
    )
    excavate_parser.add_argument(
        "--output", "-o",
        help="File path to save the output (default: stdout)"
    )
    excavate_parser.add_argument(
        "--repo", "-r",
        help="Path to git repository (default: current working directory)"
    )
    excavate_parser.add_argument(
        "--no-bypass-churn",
        action="store_true",
        help="Do not bypass cosmetic or formatting churn commits"
    )

    return parser


def main(argv=None):
    # Ensure Windows console encoding compatibility with UTF-8
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "excavate":
        try:
            excavator = Excavator(repo_path=args.repo)
            report = excavator.excavate(
                target_str=args.target,
                bypass_churn=not args.no_bypass_churn
            )

            # Output rendering
            if args.format == "terminal":
                if args.output:
                    with open(args.output, "w", encoding="utf-8") as f:
                        print_excavation_report(report, stream=f)
                    print(f"Terminal report written to {args.output}")
                else:
                    print_excavation_report(report)

            elif args.format == "html":
                html_content = generate_html_report(report)
                if args.output:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(html_content)
                    print(f"HTML report successfully generated at: {args.output}")
                else:
                    sys.stdout.write(html_content)

            elif args.format == "md":
                md_content = generate_markdown_report(report)
                if args.output:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(md_content)
                    print(f"Markdown report written to: {args.output}")
                else:
                    sys.stdout.write(md_content)

            elif args.format == "json":
                json_content = generate_json_report(report)
                if args.output:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(json_content)
                    print(f"JSON report written to: {args.output}")
                else:
                    sys.stdout.write(json_content)

        except (GitExecutionError, ValueError, FileNotFoundError) as e:
            sys.stderr.write(f"\n\033[31m[Git-Archaeologist Error]\033[0m {e}\n\n")
            sys.exit(1)
        except KeyboardInterrupt:
            sys.exit(130)


if __name__ == "__main__":
    main()
