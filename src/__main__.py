from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console

from src.config.settings import Settings
from src.data.preprocess import prepare_dataset_artifacts


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="basicRepository", add_help=True)
    sub = p.add_subparsers(dest="command", required=True)

    prep = sub.add_parser(
        "prepare-data",
        help="Phase 0: load dataset, preprocess, write artifacts",
    )
    prep.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Override artifacts directory (default: from settings)",
    )
    prep.add_argument(
        "--no-download",
        action="store_true",
        help="Fail if dataset is not already cached locally",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    console = Console()
    args = _build_parser().parse_args(argv)

    settings = Settings()
    output_dir = Path(args.output_dir) if args.output_dir else settings.artifacts_dir

    if args.command == "prepare-data":
        report = prepare_dataset_artifacts(
            dataset_name=settings.dataset_name,
            dataset_split=settings.dataset_split,
            hf_cache_dir=settings.hf_cache_dir,
            output_dir=output_dir,
            allow_download=not args.no_download,
        )
        console.print(f"[green]Wrote:[/green] {report['restaurants_jsonl_path']}")
        console.print(f"[green]Wrote:[/green] {report['preprocess_report_path']}")
        console.print("[dim]Summary:[/dim]")
        console.print_json(json.dumps(report["summary"], ensure_ascii=False))
        return 0

    console.print("[red]Unknown command[/red]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

