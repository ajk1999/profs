from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from profs.models import FacultyProfile
from profs.settings import project_root


def render_email(profile: FacultyProfile, template_path: str | None = None) -> str:
    chosen_template_path = Path(template_path) if template_path else project_root() / "templates" / "outreach_email.txt.j2"
    environment = Environment(
        loader=FileSystemLoader(str(chosen_template_path.parent)),
        autoescape=False,
        trim_blocks=False,
        lstrip_blocks=False,
        keep_trailing_newline=True,
    )
    template = environment.get_template(chosen_template_path.name)
    research_area = profile.focus_phrase or "your recent work"
    return template.render(
        first_name=profile.first_name or "there",
        research_area=research_area,
        is_security_related=profile.is_security_related,
        alignment_sentence=profile.alignment_sentence,
    )
