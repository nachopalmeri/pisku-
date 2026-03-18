"""
Context Builder — Assembles selected skills + optional agent into a single .md context file.
"""
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from cli.skills_manager import Skill
    from cli.agents_manager import Agent


class ContextBuilder:
    def __init__(self, root: Path):
        self.root = root
        self.output_dir = root / "docs" / "contexts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        project_name: str,
        skills: list["Skill"],
        agent: Optional["Agent"] = None,
    ) -> Path:
        """Build a single context .md from selected skills + optional agent."""
        safe_name = project_name.lower().replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"{safe_name}_{timestamp}.md"

        lines: list[str] = [
            f"# PISKU Context — {project_name}",
            f"> Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"> Skills    : {len(skills)}",
        ]
        if agent:
            lines.append(f"> Agent     : {agent.name}")
        lines += ["", "---", ""]

        # Agent block first — defines the LLM's role/behaviour
        if agent:
            lines += [
                f"## 🤖 Agent: `{agent.name}`",
                "",
                agent.read(),
                "",
                "---",
                "",
            ]

        lines += [
            "## Context Instructions",
            "The following skills were selected for this session.",
            "Use ONLY the patterns and conventions listed below.",
            "Do not assume context outside what is provided here.",
            "",
            "---",
            "",
        ]

        for skill in skills:
            lines += [
                f"## 📦 Skill: `{skill.name}` [{skill.category}]",
                "",
                skill.read(),
                "",
                "---",
                "",
            ]

        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path
