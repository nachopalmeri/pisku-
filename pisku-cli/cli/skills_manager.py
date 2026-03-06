"""
Skills Manager — CRUD for local skill library.
Skills are .md files organized by category.
"""
import shutil
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich import box

from cli.license_manager import LicenseManager

console = Console()

CATEGORIES = ["backend", "frontend", "web3", "devops"]


class Skill:
    def __init__(self, name: str, category: str, path: Path):
        self.name = name
        self.category = category
        self.path = path

    @property
    def size_kb(self) -> float:
        return self.path.stat().st_size / 1024

    def read(self) -> str:
        return self.path.read_text(encoding="utf-8")


class SkillsManager:
    def __init__(self, root: Path, license_mgr: LicenseManager):
        self.root = root
        self.skills_dir = root / "skills"
        self.license_mgr = license_mgr

    def _all_skills(self) -> list[Skill]:
        skills = []
        for category in CATEGORIES:
            cat_dir = self.skills_dir / category
            cat_dir.mkdir(parents=True, exist_ok=True)
            for md_file in sorted(cat_dir.glob("*.md")):
                skills.append(Skill(md_file.stem, category, md_file))
        return skills

    def count_skills(self) -> int:
        return len(self._all_skills())

    def add_skill(self, name: str, category: str, source_file: Optional[Path] = None) -> Path:
        if category not in CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}")

        dest = self.skills_dir / category / f"{name}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)

        if source_file and source_file.exists():
            shutil.copy2(source_file, dest)
        else:
            # Create template
            dest.write_text(
                f"# {name.replace('-', ' ').title()}\n\n"
                f"## Purpose\nDescribe what this skill provides to the LLM context.\n\n"
                f"## Key Patterns\n- Pattern 1\n- Pattern 2\n\n"
                f"## Examples\n```\n# Add code examples here\n```\n",
                encoding="utf-8"
            )

        return dest

    def get_skills_by_name(self, names: list[str]) -> list[Skill]:
        all_skills = self._all_skills()
        return [s for s in all_skills if s.name in names]

    def display_skills_table(self, category_filter: Optional[str] = None):
        skills = self._all_skills()
        if category_filter:
            skills = [s for s in skills if s.category == category_filter]

        if not skills:
            console.print("[yellow]No skills found.[/yellow]")
            return

        table = Table(title="📚 Available Skills", box=box.ROUNDED, border_style="cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="bold white")
        table.add_column("Category", style="cyan")
        table.add_column("Size", style="dim", justify="right")

        for i, skill in enumerate(skills, 1):
            table.add_row(
                str(i),
                skill.name,
                skill.category,
                f"{skill.size_kb:.1f} KB"
            )

        console.print(table)

    def interactive_skill_selector(self) -> list[Skill]:
        """Show numbered menu and return selected skills."""
        skills = self._all_skills()

        if not skills:
            console.print("[yellow]⚠️  No skills installed. Run [bold]pisku add-skill[/bold] first.[/yellow]")
            return []

        # Group by category
        by_category: dict[str, list[tuple[int, Skill]]] = {}
        idx = 1
        indexed: dict[int, Skill] = {}
        for skill in skills:
            if skill.category not in by_category:
                by_category[skill.category] = []
            by_category[skill.category].append((idx, skill))
            indexed[idx] = skill
            idx += 1

        # Display
        console.print("\n[bold cyan]📚 Select skills for your context:[/bold cyan]")
        console.print("[dim]Enter numbers separated by commas (e.g. 1,3,5) or 'all'[/dim]\n")

        for category, items in by_category.items():
            console.print(f"[bold yellow]── {category.upper()} ──[/bold yellow]")
            for num, skill in items:
                console.print(f"  [dim]{num:2d}.[/dim] [white]{skill.name}[/white] [dim]({skill.size_kb:.1f} KB)[/dim]")
            console.print()

        # Prompt
        raw = Prompt.ask("[bold]Your selection[/bold]", default="").strip()

        if not raw:
            return []

        if raw.lower() == "all":
            selected = list(indexed.values())
        else:
            try:
                numbers = [int(n.strip()) for n in raw.split(",") if n.strip()]
                selected = [indexed[n] for n in numbers if n in indexed]
            except ValueError:
                console.print("[red]Invalid input. Use numbers like: 1,2,3[/red]")
                return []

        # Show selection summary
        console.print(f"\n[green]✅ Selected {len(selected)} skill(s):[/green]")
        for s in selected:
            console.print(f"  • [cyan]{s.name}[/cyan] [dim]({s.category})[/dim]")

        return selected
