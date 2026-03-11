from __future__ import annotations

import csv
import json
from pathlib import Path

from profs.models import FacultyProfile


OUTPUT_FIELDS = [
    "name",
    "first_name",
    "title",
    "email",
    "personal_website",
    "profile_url",
    "university",
    "department",
    "research_text",
    "startup_signal_hard",
    "startup_evidence_hard",
    "dealflow_score",
    "publications_json",
    "focus_phrase",
    "is_security_related",
    "alignment_sentence",
    "draft_email",
    "discovery_method",
    "extraction_confidence",
    "publication_confidence",
    "no_recent_publications",
    "notes",
]


def write_outputs(profiles: list[FacultyProfile], output_dir: str) -> tuple[Path, Path]:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for profile in profiles:
        row = profile.to_output_row()
        row["publications_json"] = json.dumps(row["publications_json"], ensure_ascii=False)
        rows.append(row)

    csv_path = target_dir / "faculty_results.csv"
    json_path = target_dir / "faculty_results.json"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump([profile.to_output_row() for profile in profiles], handle, indent=2, ensure_ascii=False)

    return csv_path, json_path
