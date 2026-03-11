from __future__ import annotations

import argparse

from profs.browser_client import BrowserClient
from profs.directory_discovery import discover_faculty_pages
from profs.email_drafter import render_email
from profs.http_client import HttpClient
from profs.outputs import write_outputs
from profs.profile_parser import extract_profile
from profs.publication_lookup import lookup_publications
from profs.research_focus import summarize_research_focus
from profs.settings import load_settings, load_university_config
from profs.startup_scoring import score_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="University faculty discovery and outreach pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command_name, defaults in (
        ("run", {"max_pages": None, "max_profiles": None}),
        ("test", {"max_pages": 1, "max_profiles": 5}),
    ):
        subparser = subparsers.add_parser(command_name, help=f"{command_name} the pipeline")
        subparser.add_argument("--directory-url", required=True, help="Department or faculty directory URL")
        subparser.add_argument("--university", required=True, help="University name")
        subparser.add_argument("--department", required=True, help="Department name")
        subparser.add_argument("--config", default="", help="Optional university YAML config path")
        subparser.add_argument("--max-pages", type=int, default=defaults["max_pages"])
        subparser.add_argument("--max-profiles", type=int, default=defaults["max_profiles"])
        subparser.add_argument("--output-dir", default="", help="Directory for CSV and JSON outputs")
        subparser.add_argument(
            "--disable-browser-fallback",
            action="store_true",
            help="Skip Playwright fallback even if static discovery is weak",
        )

    return parser


def run_pipeline(args: argparse.Namespace) -> int:
    settings = load_settings()
    config = load_university_config(args.config or None)
    output_dir = args.output_dir or settings.output_dir

    http_client = HttpClient(settings)
    browser_client = BrowserClient(enabled=not args.disable_browser_fallback)

    discovered = discover_faculty_pages(
        directory_url=args.directory_url,
        http_client=http_client,
        browser_client=browser_client,
        config=config,
        max_pages=args.max_pages,
    )

    if args.max_profiles is not None:
        discovered = discovered[: args.max_profiles]

    profiles = []
    for discovered_profile in discovered:
        profile = extract_profile(
            profile_url=discovered_profile.profile_url,
            university=args.university,
            department=args.department,
            http_client=http_client,
            config=config,
        )
        profile.discovery_method = discovered_profile.discovery_method
        profile.extraction_confidence = max(profile.extraction_confidence, discovered_profile.confidence)
        profile.notes = discovered_profile.notes
        profile = score_profile(profile, config)
        profile = lookup_publications(profile, http_client)
        profile = summarize_research_focus(profile, settings)
        profile.draft_email = render_email(profile)
        profiles.append(profile)

    csv_path, json_path = write_outputs(profiles, output_dir)

    print(f"Discovered profiles: {len(discovered)}")
    print(f"Processed profiles: {len(profiles)}")
    print(f"CSV output: {csv_path}")
    print(f"JSON output: {json_path}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run_pipeline(args)


if __name__ == "__main__":
    raise SystemExit(main())
