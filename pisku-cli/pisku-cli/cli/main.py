"""
PISKU CLI — Auditor predictivo de skills para AI coding tools.

Tres comandos:
  pisku audit            → salud de todas las skills instaladas
  pisku for "tarea"      → qué skills van a disparar + costo en tokens
  pisku fix [skill]      → fixer interactivo de descripciones

Bonus:
  pisku skills pull      → instalar skills desde skills.sh / GitHub
"""
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel   import Panel
from rich.prompt  import Prompt, Confirm
from rich.table   import Table
from rich         import box

app    = typer.Typer(
    name="pisku",
    help="⚡ PISKU — Auditá tus skills antes de quemar tokens.",
    add_completion=False,
)
skills_app = typer.Typer(help="Gestión de skills remotas.")
app.add_typer(skills_app, name="skills")

console = Console()


# ══════════════════════════════════════════════════════════════════════════════
#  pisku audit
# ══════════════════════════════════════════════════════════════════════════════

@app.command()
def audit(
    fix_now: bool = typer.Option(False, "--fix", "-f", help="Iniciar fixer tras el audit"),
    tool:    Optional[str] = typer.Option(None, "--tool", "-t", help="Filtrar por tool (ej: claude-code)"),
):
    """Auditoría de salud de todas las skills instaladas."""
    from cli.skill_scanner import scan_all_skills
    from cli.skill_auditor  import run_audit

    with console.status("[dim]Escaneando skills...[/dim]"):
        skills = scan_all_skills()

    if tool:
        skills = [s for s in skills if s.tool == tool]

    if not skills:
        console.print("[yellow]No se encontraron skills instaladas.[/yellow]")
        console.print("[dim]Instalá skills con: npx skills add <owner/repo>[/dim]")
        raise typer.Exit(0)

    report = run_audit(skills)

    # ── Header ────────────────────────────────────────────────────────
    console.print()
    console.print(Panel(
        f"[bold]⚡ PISKU Skill Audit[/bold]  —  {len(skills)} skills instaladas\n"
        f"[dim]Metadata fija por sesión: ~{report.total_metadata_tokens} tokens[/dim]"
        + (f"\n[red]Ruido potencial por sesión: ~{report.savings_if_fixed} tokens[/red]"
           if report.savings_if_fixed else ""),
        border_style="cyan",
    ))

    # ── Críticas ──────────────────────────────────────────────────────
    if report.critical:
        console.print(f"\n[bold red]CRÍTICO ({len(report.critical)})[/bold red]")
        for sh in report.critical:
            console.print(f"  [red]❌[/red] [bold]{sh.skill.name}[/bold]  [dim]({sh.skill.tool})[/dim]")
            console.print(f"     [dim]\"{sh.skill.description[:80]}{'…' if len(sh.skill.description)>80 else ''}\"[/dim]")
            for issue in sh.issues:
                console.print(f"     [red]→[/red] {issue.message}")
                if issue.fix_hint:
                    console.print(f"       [dim]💡 {issue.fix_hint}[/dim]")

    # ── Advertencias ──────────────────────────────────────────────────
    if report.warning:
        console.print(f"\n[bold yellow]ADVERTENCIA ({len(report.warning)})[/bold yellow]")
        for sh in report.warning:
            console.print(f"  [yellow]⚠️ [/yellow] [bold]{sh.skill.name}[/bold]  [dim]({sh.skill.tool})[/dim]")
            console.print(f"     [dim]\"{sh.skill.description[:80]}{'…' if len(sh.skill.description)>80 else ''}\"[/dim]")
            for issue in sh.issues:
                console.print(f"     [yellow]→[/yellow] {issue.message}")

    # ── Conflictos ────────────────────────────────────────────────────
    if report.conflicts:
        console.print(f"\n[bold red]CONFLICTOS DE KEYWORDS ({len(report.conflicts)})[/bold red]")
        for c in report.conflicts:
            console.print(f"  [red]🔥[/red] [bold]{c.skill_a.name}[/bold] ↔ [bold]{c.skill_b.name}[/bold]")
            console.print(f"     Keywords superpuestos: [yellow]{', '.join(c.shared_keywords[:6])}[/yellow]")
            console.print(f"     [dim]Ambas van a disparar juntas en cualquier sesión que matchee estos términos[/dim]")

    # ── Saludables ────────────────────────────────────────────────────
    if report.healthy:
        console.print(f"\n[bold green]SALUDABLES ({len(report.healthy)})[/bold green]")
        names = ", ".join(sh.skill.name for sh in report.healthy)
        console.print(f"  [green]✅[/green] [dim]{names}[/dim]")

    console.print()

    # ── Ofrecer fix inmediato ─────────────────────────────────────────
    problematic = report.critical + report.warning
    if problematic and (fix_now or Confirm.ask(
        f"¿Fixear las {len(problematic)} skills problemáticas ahora?",
        default=False,
    )):
        for sh in problematic:
            _run_fix_for(sh.skill)


# ══════════════════════════════════════════════════════════════════════════════
#  pisku for "tarea"
# ══════════════════════════════════════════════════════════════════════════════

@app.command(name="for")
def for_session(
    task: str  = typer.Argument(..., help="Descripción de lo que vas a hacer"),
    copy: bool = typer.Option(False, "--copy", "-c", help="Copiar recomendación al portapapeles"),
    tool: Optional[str] = typer.Option(None, "--tool", "-t", help="Filtrar por tool"),
):
    """Predecí qué skills van a disparar para una tarea — antes de quemar tokens."""
    from cli.skill_scanner    import scan_all_skills
    from cli.session_predictor import predict

    with console.status("[dim]Analizando skills...[/dim]"):
        skills = scan_all_skills()

    if tool:
        skills = [s for s in skills if s.tool == tool]

    if not skills:
        console.print("[yellow]No se encontraron skills instaladas.[/yellow]")
        raise typer.Exit(0)

    pred = predict(task, skills)

    console.print()
    console.print(f"[bold]🔮 Predicción para:[/bold] [cyan]\"{task}\"[/cyan]")
    console.print(f"[dim]{len(skills)} skills escaneadas[/dim]")

    # ── Van a disparar ────────────────────────────────────────────────
    if pred.will_fire:
        console.print(f"\n[bold green]VAN A DISPARAR — certeza alta ({len(pred.will_fire)})[/bold green]")
        for p in pred.will_fire:
            console.print(f"  [green]✅[/green] [bold]/{p.skill.slug}[/bold]  [dim]~{p.skill.body_tokens} tokens[/dim]")
            console.print(f"     [dim]\"{p.skill.description[:70]}{'…' if len(p.skill.description)>70 else ''}\"[/dim]")
            console.print(f"     [dim]Matcheó en: {', '.join(p.matched_on[:5])}[/dim]")
    else:
        console.print("\n[yellow]Ninguna skill matchea claramente esta tarea.[/yellow]")
        console.print("[dim]Puede que necesites instalar más skills, o que las descripciones sean muy genéricas.[/dim]")

    # ── Podrían disparar ──────────────────────────────────────────────
    if pred.might_fire:
        console.print(f"\n[bold yellow]PODRÍAN DISPARAR — descripciones problemáticas ({len(pred.might_fire)})[/bold yellow]")
        for p in pred.might_fire:
            console.print(f"  [yellow]⚡[/yellow] [bold]{p.skill.slug}[/bold]  [dim]~{p.skill.body_tokens} tokens de ruido[/dim]")
            console.print(f"     [dim]\"{p.skill.description[:70]}{'…' if len(p.skill.description)>70 else ''}\"[/dim]")
            console.print(f"     [dim]{p.reason}[/dim]")

    # ── No disparan ───────────────────────────────────────────────────
    if pred.wont_fire:
        console.print(f"\n[dim]No disparan ({len(pred.wont_fire)}): "
                      + ", ".join(p.skill.slug for p in pred.wont_fire[:8])
                      + ("…" if len(pred.wont_fire) > 8 else "") + "[/dim]")

    # ── Costo estimado ────────────────────────────────────────────────
    console.print()
    console.print(Panel(
        f"💰 [bold]Costo estimado para esta sesión[/bold]\n\n"
        f"  Metadata fija  : [cyan]~{pred.metadata_tokens} tokens[/cyan]  (siempre, toda sesión)\n"
        f"  Skills útiles  : [cyan]~{pred.fire_tokens} tokens[/cyan]\n"
        f"  Ruido potencial: [red]~{pred.noise_tokens} tokens[/red]"
        + (f"\n\n  [bold]Si fixeás las {len(pred.might_fire)} problemáticas → ahorrás [green]~{pred.savings_if_fixed} tokens[/green] por sesión[/bold]"
           if pred.might_fire else "\n\n  [green]✅ Sin ruido potencial detectado[/green]"),
        border_style="dim",
    ))

    # ── Output para pegar ─────────────────────────────────────────────
    clipboard_text = pred.clipboard_text()
    console.print(f"\n[dim]Para pegar al inicio de tu sesión:[/dim]")
    console.print(Panel(clipboard_text, border_style="green"))

    if copy:
        try:
            import pyperclip
            pyperclip.copy(clipboard_text)
            console.print("[green]📋 Copiado al portapapeles.[/green]")
        except ImportError:
            console.print("[yellow]pip install pyperclip para usar --copy[/yellow]")

    # ── Ofrecer fix de problemáticas ──────────────────────────────────
    if pred.might_fire and Confirm.ask(
        f"\n¿Fixear ahora las {len(pred.might_fire)} skills problemáticas?",
        default=False,
    ):
        for p in pred.might_fire:
            _run_fix_for(p.skill)


# ══════════════════════════════════════════════════════════════════════════════
#  pisku fix
# ══════════════════════════════════════════════════════════════════════════════

@app.command()
def fix(
    skill_name: Optional[str] = typer.Argument(None, help="Nombre de la skill a fixear (o todas si no se especifica)"),
):
    """Fixer interactivo de descripciones de skills."""
    from cli.skill_scanner import scan_all_skills, find_skill
    from cli.skill_auditor  import score_skill, run_audit

    with console.status("[dim]Escaneando skills...[/dim]"):
        all_skills = scan_all_skills()

    if not all_skills:
        console.print("[yellow]No se encontraron skills instaladas.[/yellow]")
        raise typer.Exit(0)

    # ── Fix skill específica ──────────────────────────────────────────
    if skill_name:
        skill = find_skill(skill_name, all_skills)
        if not skill:
            console.print(f"[red]Skill '{skill_name}' no encontrada.[/red]")
            console.print(f"[dim]Skills disponibles: {', '.join(s.name for s in all_skills[:10])}[/dim]")
            raise typer.Exit(1)
        _run_fix_for(skill)
        return

    # ── Fix todas las problemáticas ───────────────────────────────────
    report = run_audit(all_skills)
    to_fix = report.critical + report.warning

    if not to_fix:
        console.print("[green]✅ Todas las skills tienen descripciones saludables.[/green]")
        raise typer.Exit(0)

    console.print(f"\n[bold]{len(to_fix)} skills necesitan atención:[/bold]")
    for sh in to_fix:
        icon = "❌" if sh.level == "critical" else "⚠️ "
        console.print(f"  {icon} {sh.skill.name}")

    console.print()
    for sh in to_fix:
        if Confirm.ask(f"¿Fixear [bold]{sh.skill.name}[/bold]?", default=True):
            _run_fix_for(sh.skill)
        else:
            console.print(f"  [dim]Saltando {sh.skill.name}[/dim]")


def _run_fix_for(skill) -> None:
    """Interactive fix wizard for a single skill."""
    from cli.skill_scanner import update_description
    from cli.skill_auditor  import score_skill

    console.print()
    console.print(Panel(
        f"[bold]🔧 Fixing: {skill.name}[/bold]\n"
        f"[dim]{skill.path}[/dim]",
        border_style="cyan",
    ))

    console.print(f"\n  Descripción actual:\n  [yellow]\"{skill.description}\"[/yellow]")

    sh = score_skill(skill)
    if sh.issues:
        console.print("\n  Problemas detectados:")
        for issue in sh.issues:
            console.print(f"  [red]→[/red] {issue.message}")
            if issue.fix_hint:
                console.print(f"    [dim]💡 {issue.fix_hint}[/dim]")

    console.print()
    console.print(f"  [dim]¿Para qué usás esta skill? Describí los casos específicos.[/dim]")
    console.print(f"  [dim]Ej: 'async/await patterns, type hints, module structure'[/dim]")
    use_cases = Prompt.ask("  Casos de uso").strip()

    if not use_cases:
        console.print("  [dim]Saltando.[/dim]")
        return

    # Generate optimized description following the spec pattern:
    # "<what it does>. Use when <specific trigger conditions>."
    skill_label = skill.name.replace("-", " ")
    suggested = (
        f"{use_cases.capitalize()}. "
        f"Use when working with {skill_label} or when the task involves "
        f"{', '.join(use_cases.split(',')[:2]).strip().lower()}."
    )
    # Trim to under 200 chars if too long
    if len(suggested) > 200:
        suggested = suggested[:197] + "..."

    console.print(f"\n  Descripción sugerida:")
    console.print(f"  [green]\"{suggested}\"[/green]")
    console.print(f"  [dim]({len(suggested)} chars)[/dim]")

    console.print()
    action = Prompt.ask(
        "  ¿Qué hacemos?",
        choices=["usar", "editar", "saltar"],
        default="usar",
    )

    if action == "editar":
        suggested = Prompt.ask("  Nueva descripción", default=suggested).strip()

    if action == "saltar":
        console.print("  [dim]Saltado.[/dim]")
        return

    if update_description(skill, suggested):
        console.print(f"  [green]✅ Guardado.[/green]")
        console.print(f"  [dim]Antes: \"{skill.description[:60]}\"[/dim]")
        console.print(f"  [dim]Ahora:  \"{suggested[:60]}\"[/dim]")
    else:
        console.print(f"  [red]❌ No se pudo escribir en {skill.path}[/red]")


# ══════════════════════════════════════════════════════════════════════════════
#  pisku skills pull  (instalar desde skills.sh / GitHub)
# ══════════════════════════════════════════════════════════════════════════════

@skills_app.command("pull")
def skills_pull(
    source:     str           = typer.Argument(..., help="GitHub repo: owner/repo o URL"),
    skill_name: Optional[str] = typer.Option(None, "--skill", "-s", help="Skill específica"),
    yes:        bool          = typer.Option(False, "--yes", "-y", help="Saltear confirmación"),
):
    """Instalar skills desde skills.sh o cualquier repo de GitHub."""
    from cli.skills_puller import SkillsPuller, OfflineError
    from cli.skill_scanner import scan_all_skills

    # Default install dir: ~/.claude/skills/ (el standard de la industria)
    install_dir = Path.home() / ".claude" / "skills"

    puller = SkillsPuller(user_skills_dir=install_dir)

    if skill_name:
        result = puller.install_direct(source, skill_name, yes=yes)
        if not result:
            raise typer.Exit(1)
    else:
        try:
            results = puller.interactive_install(source)
        except OfflineError:
            console.print("[yellow]⚠️  Sin conexión a GitHub.[/yellow]")
            raise typer.Exit(1)
        if not results:
            raise typer.Exit(0)

    console.print(
        "\n[dim]Tip: corré [bold]pisku audit[/bold] para verificar "
        "la salud de las nuevas skills.[/dim]"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  pisku version
# ══════════════════════════════════════════════════════════════════════════════

@app.command()
def version():
    """Versión de PISKU."""
    console.print("[bold cyan]⚡ PISKU[/bold cyan] [dim]v0.3.0[/dim]")
    console.print("[dim]Auditor predictivo de skills para AI coding tools.[/dim]")


if __name__ == "__main__":
    app()
