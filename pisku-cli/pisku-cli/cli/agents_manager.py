"""
PISKU Agents Manager — select and inject agent .md files into context.
Agents live in skills/agents/ (system) or ~/.pisku/agents/ (user).
"""
import json
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich import box

console = Console()

FREE_AGENT_LIMIT = 3
ACTIVE_AGENT_FILE = Path.home() / ".pisku" / "active_agent.json"


class Agent:
    def __init__(self, name: str, path: Path, source: str = "system"):
        self.name = name
        self.path = path
        self.source = source  # "system" | "user"

    @property
    def description(self) -> str:
        """Extract first non-empty line after the # title."""
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
            for line in lines[1:]:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Trim markdown bold markers and cut after period
                    clean = line.replace("**", "").replace("*", "")
                    return clean[:60] + ("…" if len(clean) > 60 else "")
        except Exception:
            pass
        return ""

    @property
    def is_system(self) -> bool:
        return self.source == "system"

    def read(self) -> str:
        return self.path.read_text(encoding="utf-8")


class AgentsManager:
    def __init__(self, root: Path, is_pro: bool = False):
        self.root = root
        self.is_pro = is_pro
        self.system_dir = root / "skills" / "agents"
        self.user_dir = Path.home() / ".pisku" / "agents"
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self.system_dir.mkdir(parents=True, exist_ok=True)

    # ── Read ─────────────────────────────────────────────────────────

    def all_agents(self) -> list[Agent]:
        agents: list[Agent] = []
        for md in sorted(self.system_dir.glob("*.md")):
            agents.append(Agent(md.stem, md, "system"))
        for md in sorted(self.user_dir.glob("*.md")):
            if md.stem not in {a.name for a in agents}:
                agents.append(Agent(md.stem, md, "user"))

        # FREE: cap to 3
        if not self.is_pro:
            agents = agents[:FREE_AGENT_LIMIT]
        return agents

    def get(self, name: str) -> Optional[Agent]:
        for a in self.all_agents():
            if a.name == name:
                return a
        return None

    def list_all(self) -> list[Agent]:
        """Alias for all_agents() — used by pisku init."""
        return self.all_agents()

    def get_by_name(self, name: str) -> Optional[Agent]:
        """Alias for get() — used by pisku init after agent builder."""
        return self.get(name)

    # ── Active agent persistence ─────────────────────────────────────

    def get_active(self) -> Optional[str]:
        if ACTIVE_AGENT_FILE.exists():
            try:
                data = json.loads(ACTIVE_AGENT_FILE.read_text(encoding="utf-8"))
                return data.get("name")
            except Exception:
                pass
        return None

    def set_active(self, name: str) -> None:
        ACTIVE_AGENT_FILE.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_AGENT_FILE.write_text(
            json.dumps({"name": name}, indent=2), encoding="utf-8"
        )

    def clear_active(self) -> None:
        if ACTIVE_AGENT_FILE.exists():
            ACTIVE_AGENT_FILE.unlink()

    # ── Display ──────────────────────────────────────────────────────

    def display_table(self) -> None:
        agents = self.all_agents()
        active = self.get_active()

        if not agents:
            console.print("[yellow]No agents found.[/yellow]")
            return

        table = Table(
            title="🤖 Available Agents",
            box=box.ROUNDED,
            border_style="violet",
            show_footer=False,
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="bold white")
        table.add_column("Description", style="dim")
        table.add_column("Status", width=10)

        for i, agent in enumerate(agents, 1):
            status = "[green]● active[/green]" if agent.name == active else ""
            table.add_row(str(i), agent.name, agent.description, status)

        console.print(table)

        tier_info = (
            f"[dim]PRO: unlimited agents[/dim]"
            if self.is_pro
            else f"[dim]FREE: {len(agents)}/{FREE_AGENT_LIMIT} agents · [yellow]pisku activate-pro <key>[/yellow] for more[/dim]"
        )
        console.print(f"\n  {tier_info}\n")

    # ── Interactive selector (called from pisku init) ─────────────────

    def interactive_selector(self) -> Optional[Agent]:
        """
        Prompt user to optionally pick one agent for this session.
        Returns the selected Agent or None.
        """
        agents = self.all_agents()
        active = self.get_active()

        console.print("\n[bold violet]🤖 Add an agent to this context? [dim](optional)[/dim][/bold violet]")
        console.print("[dim]Agents define the LLM's role/behaviour for this session.[/dim]\n")

        for i, agent in enumerate(agents, 1):
            marker = " [green]●[/green]" if agent.name == active else ""
            console.print(f"  [dim]{i:2d}.[/dim] [white]{agent.name}[/white]{marker} [dim]— {agent.description}[/dim]")

        console.print(f"  [dim] 0.[/dim] [dim]Skip — no agent[/dim]")
        console.print()

        raw = Prompt.ask("[bold]Selection[/bold]", default="0").strip()
        try:
            n = int(raw)
        except ValueError:
            return None

        if n == 0:
            return None
        if 1 <= n <= len(agents):
            return agents[n - 1]
        return None

    # ── CRUD ─────────────────────────────────────────────────────────

    def add_agent(self, name: str, source_file: Optional[Path] = None) -> Path:
        dest = self.user_dir / f"{name}.md"
        if source_file and source_file.exists():
            import shutil
            shutil.copy2(source_file, dest)
        else:
            dest.write_text(
                f"# Agent: {name.replace('-', ' ').title()}\n\n"
                "Describí el rol y comportamiento del agente aquí.\n\n"
                "## Tu rol\n- \n\n## Formato de respuesta\n- \n",
                encoding="utf-8",
            )
        return dest

    def remove_agent(self, name: str) -> bool:
        agent = self.get(name)
        if not agent:
            return False
        if agent.source == "system":
            console.print("[red]No podés eliminar agents del sistema.[/red]")
            return False
        agent.path.unlink()
        if self.get_active() == name:
            self.clear_active()
        return True
