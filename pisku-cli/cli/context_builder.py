"""
Context Builder — Assembles selected skills into a single .md context file.
"""
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli.skills_manager import Skill


class ContextBuilder:
    def __init__(self, root: Path):
        self.root = root
        self.output_dir = root / "docs" / "contexts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(self, project_name: str, skills: list["Skill"]) -> Path:
        """Build a single context .md file from selected skills."""
        safe_name = project_name.lower().replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"{safe_name}_{timestamp}.md"

        lines = [
            f"# PISKU Context — {project_name}",
            f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"> Skills included: {len(skills)}",
            "",
            "---",
            "",
            "## Instructions for LLM",
            "The following context was curated specifically for this project.",
            "Use ONLY the skills listed below when answering questions.",
            "Do not assume context outside of what is provided here.",
            "",
            "---",
            "",
        ]

        for skill in skills:
            lines.append(f"## 📦 Skill: `{skill.name}` [{skill.category}]")
            lines.append("")
            lines.append(skill.read())
            lines.append("")
            lines.append("---")
            lines.append("")

        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path
