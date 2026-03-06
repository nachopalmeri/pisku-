"""
Stats Tracker — Records usage history in JSON.
FREE: Shows total savings only.
PRO: Full dashboard with per-project breakdown and CSV export.
"""
import csv
import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

STATS_FILE = "config/stats.json"


class StatsTracker:
    def __init__(self, root: Path):
        self.root = root
        self.stats_path = root / STATS_FILE
        self._data: dict | None = None

    def _load(self) -> dict:
        if self._data is None:
            if self.stats_path.exists():
                with open(self.stats_path) as f:
                    self._data = json.load(f)
            else:
                self._data = {"sessions": [], "total_tokens_saved": 0}
        return self._data

    def _save(self):
        self.stats_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.stats_path, "w") as f:
            json.dump(self._data, f, indent=2)

    def get_active_projects(self) -> list[str]:
        data = self._load()
        # A project is "active" if it has sessions
        projects = {s["project"] for s in data["sessions"]}
        return list(projects)

    def record_session(self, project: str, skills: list, tokens_saved: int):
        data = self._load()
        session = {
            "project": project,
            "timestamp": datetime.now().isoformat(),
            "skills": [s.name for s in skills],
            "skill_count": len(skills),
            "tokens_saved": tokens_saved,
        }
        data["sessions"].append(session)
        data["total_tokens_saved"] = data.get("total_tokens_saved", 0) + tokens_saved
        self._save()

    def display_summary(self):
        """FREE tier: simple total."""
        data = self._load()
        total = data.get("total_tokens_saved", 0)
        sessions = len(data.get("sessions", []))
        projects = len(set(s["project"] for s in data.get("sessions", [])))

        console.print(Panel(
            f"[bold cyan]📊 PISKU Stats[/bold cyan] [dim](FREE tier)[/dim]\n\n"
            f"  💰 Total tokens saved:  [bold green]{total:,}[/bold green]\n"
            f"  🗂️  Total sessions:      [bold]{sessions}[/bold]\n"
            f"  📁 Projects tracked:   [bold]{projects}[/bold]\n\n"
            f"[dim]→ Upgrade to PRO for detailed dashboard: [bold]pisku activate-pro <key>[/bold][/dim]",
            border_style="cyan"
        ))

    def display_dashboard(self):
        """PRO tier: full breakdown."""
        data = self._load()
        sessions = data.get("sessions", [])

        if not sessions:
            console.print("[yellow]No sessions recorded yet.[/yellow]")
            return

        # Per-project breakdown
        projects: dict[str, dict] = {}
        for s in sessions:
            p = s["project"]
            if p not in projects:
                projects[p] = {"sessions": 0, "tokens_saved": 0, "skills_used": set()}
            projects[p]["sessions"] += 1
            projects[p]["tokens_saved"] += s["tokens_saved"]
            projects[p]["skills_used"].update(s["skills"])

        table = Table(title="⚡ PRO Dashboard — Token Savings by Project", box=box.ROUNDED, border_style="gold1")
        table.add_column("Project", style="bold white")
        table.add_column("Sessions", justify="right", style="cyan")
        table.add_column("Tokens Saved", justify="right", style="green")
        table.add_column("Unique Skills", justify="right", style="dim")

        for project, info in sorted(projects.items(), key=lambda x: -x[1]["tokens_saved"]):
            table.add_row(
                project,
                str(info["sessions"]),
                f"{info['tokens_saved']:,}",
                str(len(info["skills_used"]))
            )

        console.print(table)
        console.print(f"\n[bold]Total:[/bold] [green]{data.get('total_tokens_saved', 0):,}[/green] tokens saved across {len(sessions)} sessions")

    def export_csv(self) -> Path:
        """PRO: Export session history as CSV."""
        data = self._load()
        sessions = data.get("sessions", [])
        output = self.root / "docs" / "pisku_stats_export.csv"
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["project", "timestamp", "skill_count", "tokens_saved", "skills"])
            writer.writeheader()
            for s in sessions:
                writer.writerow({
                    "project": s["project"],
                    "timestamp": s["timestamp"],
                    "skill_count": s["skill_count"],
                    "tokens_saved": s["tokens_saved"],
                    "skills": "|".join(s.get("skills", [])),
                })

        return output
