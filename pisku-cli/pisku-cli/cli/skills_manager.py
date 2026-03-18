"""
Skills Manager — CRUD for local skill library + interactive menu with
recommendations support.
"""
import shutil
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box

from cli.license_manager import LicenseManager

console = Console()

CATEGORIES = ["backend", "frontend", "web3", "devops", "testing"]
FREE_SKILL_LIMIT = 10


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
        self.user_skills_dir = Path.home() / ".pisku" / "skills"

    def _all_skills(self) -> list[Skill]:
        skills: list[Skill] = []
        seen_names: set[str] = set()
        for category in CATEGORIES:
            for md in sorted((self.skills_dir / category).glob("*.md")):
                skills.append(Skill(md.stem, category, md))
                seen_names.add(md.stem)
            user_cat = self.user_skills_dir / category
            if user_cat.exists():
                for md in sorted(user_cat.glob("*.md")):
                    if md.stem not in seen_names:
                        skills.append(Skill(md.stem, category, md))
                        seen_names.add(md.stem)
        return skills

    def count_skills(self) -> int:
        return len(self._all_skills())

    def get_skills_by_name(self, names: list[str]) -> list[Skill]:
        return [s for s in self._all_skills() if s.name in names]

    def display_skills_table(
        self,
        category_filter: Optional[str] = None,
        search: Optional[str] = None,
        user_only: bool = False,
    ) -> None:
        skills = self._all_skills()
        if category_filter:
            skills = [s for s in skills if s.category == category_filter]
        if search:
            q = search.lower()
            skills = [s for s in skills if q in s.name.lower()]
        if user_only:
            user_dir = str(self.user_skills_dir)
            skills = [s for s in skills if str(s.path).startswith(user_dir)]

        if not skills:
            console.print("[yellow]No skills match your filter.[/yellow]")
            return

        table = Table(title="📚 Available Skills", box=box.ROUNDED, border_style="cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="bold white")
        table.add_column("Category", style="cyan")
        table.add_column("Size", style="dim", justify="right")
        for i, skill in enumerate(skills, 1):
            table.add_row(str(i), skill.name, skill.category, f"{skill.size_kb:.1f} KB")
        console.print(table)

        total = len(self._all_skills())
        if not self.license_mgr.is_pro():
            console.print(
                f"\n  [dim]FREE tier: {total}/{FREE_SKILL_LIMIT} skills · "
                "[yellow]pisku activate-pro <key>[/yellow] for unlimited[/dim]\n"
            )

    def interactive_skill_selector(self, recommendations: Optional[dict] = None) -> list[Skill]:
        skills = self._all_skills()
        if not skills:
            console.print("[yellow]⚠️  No skills found. Run pisku skills add first.[/yellow]")
            return []
        return self._render_menu(skills, recommendations)

    def _render_menu(self, skills: list[Skill], recommendations: Optional[dict]) -> list[Skill]:
        indexed: dict[int, Skill] = {}
        by_category: dict[str, list[tuple[int, Skill]]] = {}
        idx = 1
        for skill in skills:
            indexed[idx] = skill
            by_category.setdefault(skill.category, []).append((idx, skill))
            idx += 1

        rec_indices: list[int] = []
        rec_reason = ""
        if recommendations:
            rec_names = set(recommendations.get("skills", []))
            rec_reason = recommendations.get("reason", "")
            rec_indices = [i for i, s in indexed.items() if s.name in rec_names]

        self._print_menu(by_category, rec_indices, rec_reason)

        while True:
            raw = Prompt.ask(
                "[bold]Tu selección[/bold] [dim](ej: 1,3  1-5  all  backend  /python)[/dim]",
                default="",
            ).strip()

            if not raw:
                return []

            # Search
            if raw.startswith("/"):
                query = raw[1:].lower()
                filtered = [s for s in skills if query in s.name.lower() or query in s.category.lower()]
                if not filtered:
                    console.print(f"[yellow]No skills match '{query}'[/yellow]")
                    self._print_menu(by_category, rec_indices, rec_reason)
                    continue
                console.print(f"\n[dim]Results for:[/dim] [cyan]{query}[/cyan]\n")
                return self._render_menu(filtered, None)

            # Use recommendations
            if raw.lower() == "rec" and rec_indices:
                selected = [indexed[i] for i in rec_indices if i in indexed]
                self._print_selected(selected)
                return selected

            # All
            if raw.lower() == "all":
                self._print_selected(list(indexed.values()))
                return list(indexed.values())

            # Category shortcut
            if raw.lower() in CATEGORIES:
                cat_skills = [s for s in skills if s.category == raw.lower()]
                if not cat_skills:
                    console.print(f"[yellow]No skills in '{raw}'[/yellow]")
                    continue
                self._print_selected(cat_skills)
                return cat_skills

            # Numbers / ranges
            try:
                numbers: list[int] = []
                for part in raw.replace(" ", "").split(","):
                    if "-" in part:
                        a, b = part.split("-", 1)
                        numbers.extend(range(int(a), int(b) + 1))
                    else:
                        numbers.append(int(part))
                selected = [indexed[n] for n in numbers if n in indexed]
                if not selected:
                    console.print("[red]Ningún número válido.[/red]")
                    continue
                self._print_selected(selected)
                return selected
            except ValueError:
                console.print("[red]Formato inválido.[/red] Usá: 1,3  1-5  all  backend  /python  rec")

    def _print_menu(self, by_category: dict, rec_indices: list[int], rec_reason: str) -> None:
        console.print()
        console.print(Panel("[bold violet]📦 PISKU — Context Selector[/bold violet]", border_style="violet", padding=(0, 2)))

        if rec_indices and rec_reason:
            rec_str = ",".join(str(i) for i in rec_indices)
            console.print(
                f"\n  [bold green]🎯 Recomendación:[/bold green] {rec_reason}\n"
                f"  [dim]→ Skills sugeridas:[/dim] [green]{rec_str}[/green]  [dim](escribí 'rec')[/dim]\n"
            )

        for category, items in by_category.items():
            console.print(f"  [bold yellow]── {category.upper()} ──[/bold yellow]")
            for num, skill in items:
                star = " [green]★[/green]" if num in rec_indices else ""
                console.print(f"    [dim]{num:2d}.[/dim] [white]{skill.name}[/white]  [dim]({skill.size_kb:.1f} KB)[/dim]{star}")
            console.print()

        console.print("  [dim]Atajos:[/dim] [cyan]1,3,5[/cyan]  [cyan]1-5[/cyan]  [cyan]all[/cyan]  [cyan]backend[/cyan]  [cyan]/python[/cyan]  [cyan]rec[/cyan]\n")

    def _print_selected(self, selected: list[Skill]) -> None:
        total_kb = sum(s.size_kb for s in selected)
        console.print(f"\n  [green]✅ {len(selected)} skill(s) seleccionadas ({total_kb:.1f} KB):[/green]")
        for s in selected:
            console.print(f"    [dim]•[/dim] [cyan]{s.name}[/cyan]  [dim]({s.category})[/dim]")
        console.print()

    def add_skill(self, name: str, category: str, source_file: Optional[Path] = None) -> Path:
        if category not in CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}")
        dest = self.user_skills_dir / category / f"{name}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source_file and source_file.exists():
            shutil.copy2(source_file, dest)
        else:
            dest.write_text(
                f"# {name.replace('-', ' ').title()}\n\n"
                "## Purpose\nDescribe what this skill provides to the LLM context.\n\n"
                "## Key Patterns\n- Pattern 1\n\n## Examples\n```\n# code here\n```\n",
                encoding="utf-8",
            )
        return dest

    def remove_skill(self, name: str) -> bool:
        for cat in CATEGORIES:
            p = self.user_skills_dir / cat / f"{name}.md"
            if p.exists():
                p.unlink()
                return True
        if any((self.skills_dir / cat / f"{name}.md").exists() for cat in CATEGORIES):
            console.print(f"[red]'{name}' es una skill del sistema y no puede eliminarse.[/red]")
        return False
