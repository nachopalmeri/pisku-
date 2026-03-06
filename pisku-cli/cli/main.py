"""
PISKU CLI — Token-aware context selector for LLM workflows
"""
import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from cli.skills_manager import SkillsManager
from cli.context_builder import ContextBuilder
from cli.token_calculator import TokenCalculator
from cli.license_manager import LicenseManager
from cli.stats_tracker import StatsTracker
from cli.clipboard_manager import copy_file_to_clipboard

app = typer.Typer(
    name="pisku",
    help="🧠 PISKU — Stop wasting tokens on irrelevant context.",
    add_completion=False,
)

console = Console()
ROOT = Path(__file__).parent.parent


def get_managers():
    license_mgr = LicenseManager(ROOT)
    stats = StatsTracker(ROOT)
    skills = SkillsManager(ROOT, license_mgr)
    token_calc = TokenCalculator()
    ctx_builder = ContextBuilder(ROOT)
    return license_mgr, stats, skills, token_calc, ctx_builder


@app.command()
def init(
    project_name: str = typer.Argument(..., help="Name of your project"),
    copy: bool = typer.Option(False, "--copy", "-c", help="Copy context to clipboard after building"),
):
    """Initialize a new PISKU project and select relevant skills."""
    license_mgr, stats, skills_mgr, token_calc, ctx_builder = get_managers()

    console.print(Panel(
        f"[bold cyan]PISKU[/bold cyan] — Initializing project: [bold]{project_name}[/bold]\n"
        f"Tier: [bold {'gold1' if license_mgr.is_pro() else 'white'}]{'⚡ PRO' if license_mgr.is_pro() else '🆓 FREE'}[/bold {'gold1' if license_mgr.is_pro() else 'white'}]",
        border_style="cyan"
    ))

    # Check project limits
    if not license_mgr.is_pro():
        active = stats.get_active_projects()
        if len(active) >= 1 and project_name not in active:
            console.print(
                "[red]❌ FREE tier allows only 1 active project.[/red]\n"
                "[yellow]→ Upgrade to PRO: [bold]pisku activate-pro <key>[/bold][/yellow]"
            )
            raise typer.Exit(1)

    # Show skill menu
    selected = skills_mgr.interactive_skill_selector()
    if not selected:
        console.print("[yellow]No skills selected. Exiting.[/yellow]")
        raise typer.Exit(0)

    # Build context
    output_path = ctx_builder.build(project_name, selected)
    tokens_saved = token_calc.estimate_savings(selected)

    stats.record_session(project_name, selected, tokens_saved)

    console.print(f"\n[green]✅ Context saved to:[/green] [bold]{output_path}[/bold]")
    console.print(f"[cyan]💰 Estimated tokens saved:[/cyan] [bold]{tokens_saved:,}[/bold]")

    if copy:
        ok = copy_file_to_clipboard(output_path)
        if ok:
            console.print("[green]📋 Context copied to clipboard![/green] Paste it in your AI chat with Ctrl+V")
        else:
            console.print("[yellow]⚠️  Clipboard unavailable. Install pyperclip: pip install pyperclip[/yellow]")


@app.command(name="add-skill")
def add_skill(
    name: str = typer.Argument(..., help="Skill name (e.g. 'fastapi-auth')"),
    category: str = typer.Option("backend", "--category", "-c", help="Category: backend/frontend/web3/devops"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Path to existing .md file"),
):
    """Add a new skill to your local library."""
    license_mgr, _, skills_mgr, _, _ = get_managers()

    if not license_mgr.is_pro():
        count = skills_mgr.count_skills()
        if count >= 10:
            console.print(
                f"[red]❌ FREE tier limit: 10 skills (you have {count}).[/red]\n"
                "[yellow]→ Upgrade to PRO: [bold]pisku activate-pro <key>[/bold][/yellow]"
            )
            raise typer.Exit(1)

    result = skills_mgr.add_skill(name, category, file)
    console.print(f"[green]✅ Skill added:[/green] [bold]{result}[/bold]")


@app.command(name="list")
def list_skills(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
):
    """List all available skills, optionally filtered by category."""
    _, _, skills_mgr, _, _ = get_managers()
    skills_mgr.display_skills_table(category)


@app.command(name="build-context")
def build_context(
    project: str = typer.Argument(..., help="Project name"),
    skills: Optional[str] = typer.Option(None, "--skills", "-s", help="Comma-separated skill names"),
    copy: bool = typer.Option(False, "--copy", "-c", help="Copy context to clipboard after building"),
):
    """Build context file for a project (non-interactive)."""
    _, _, skills_mgr, token_calc, ctx_builder = get_managers()

    if skills:
        skill_list = [s.strip() for s in skills.split(",")]
        selected = skills_mgr.get_skills_by_name(skill_list)
    else:
        selected = skills_mgr.interactive_skill_selector()

    if not selected:
        console.print("[yellow]No skills selected.[/yellow]")
        raise typer.Exit(0)

    output_path = ctx_builder.build(project, selected)
    tokens_saved = token_calc.estimate_savings(selected)
    console.print(f"[green]✅ Context:[/green] {output_path} | [cyan]Tokens saved:[/cyan] {tokens_saved:,}")

    if copy:
        ok = copy_file_to_clipboard(output_path)
        if ok:
            console.print("[green]📋 Copied to clipboard![/green] Paste with Ctrl+V")
        else:
            console.print("[yellow]⚠️  Clipboard unavailable.[/yellow]")


@app.command()
def stats(
    detailed: bool = typer.Option(False, "--detailed", "-d", help="[PRO] Full dashboard with history"),
    export_csv: bool = typer.Option(False, "--csv", help="[PRO] Export usage history as CSV"),
):
    """Show token savings stats."""
    license_mgr, stats_tracker, _, _, _ = get_managers()

    if (detailed or export_csv) and not license_mgr.is_pro():
        console.print(
            "[red]❌ Detailed stats require PRO tier.[/red]\n"
            "[yellow]→ Upgrade: [bold]pisku activate-pro <key>[/bold][/yellow]"
        )
        raise typer.Exit(1)

    if detailed:
        stats_tracker.display_dashboard()
    elif export_csv:
        path = stats_tracker.export_csv()
        console.print(f"[green]✅ Exported:[/green] {path}")
    else:
        stats_tracker.display_summary()


@app.command(name="activate-pro")
def activate_pro(
    license_key: str = typer.Argument(..., help="Your PRO license key"),
):
    """Activate PRO tier with a license key (validated online)."""
    license_mgr, _, _, _, _ = get_managers()

    console.print("[cyan]🔑 Validating license key...[/cyan]")
    result = license_mgr.activate(license_key)

    if result["success"]:
        console.print(Panel(
            f"[bold green]⚡ PRO ACTIVATED![/bold green]\n"
            f"Key: {license_key[:12]}...\n"
            f"Valid until: {result.get('expires', 'Lifetime')}",
            border_style="green"
        ))
    else:
        console.print(f"[red]❌ Activation failed:[/red] {result['error']}")
        raise typer.Exit(1)


@app.command()
def version():
    """Show PISKU version and tier info."""
    license_mgr, _, _, _, _ = get_managers()
    tier = "⚡ PRO" if license_mgr.is_pro() else "🆓 FREE"
    console.print(f"[bold cyan]PISKU[/bold cyan] v0.1.0 — {tier}")


def main():
    app()


if __name__ == "__main__":
    main()
