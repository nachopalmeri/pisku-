"""
PISKU Agent Builder — wizard de 4 preguntas para generar agents .md personalizados.

Genera un agent.md bien estructurado que el LLM puede seguir como system prompt.
El archivo se guarda en ~/.pisku/agents/ y aparece en el menú de agents de pisku init.
"""
import re
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

console = Console()

# ── Opciones de pregunta 2 (prioridades) ─────────────────────────────────────
PRIORITIES = [
    ("Security",     "security"),
    ("Performance",  "performance"),
    ("Cost",         "cost"),
    ("Scalability",  "scalability"),
    ("Readability",  "readability"),
    ("Maintainability", "maintainability"),
]

# ── Opciones de pregunta 4 (formato de respuesta) ────────────────────────────
FORMATS = [
    ("Bullet points",          "Respondé con bullet points concisos. Evitá párrafos largos."),
    ("Explicación detallada",  "Explicá el razonamiento paso a paso antes de dar la solución."),
    ("Código + explicación",   "Mostrá código funcional primero, luego explicá las decisiones clave."),
]


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s\-]", "", text)
    text = re.sub(r"[\s\-]+", "-", text)
    return text[:50].strip("-") or "custom-agent"


def _parse_multi_selection(raw: str, options: list) -> list[tuple[str, str]]:
    """Parse '1,3,4' into list of matching (label, key) tuples."""
    selected = []
    seen = set()
    indexed = {i + 1: o for i, o in enumerate(options)}
    for part in raw.replace(" ", "").split(","):
        try:
            n = int(part)
            if n in indexed and n not in seen:
                selected.append(indexed[n])
                seen.add(n)
        except ValueError:
            continue
    return selected


def _generate_agent_md(rol: str, priorities: list[str], techs: str, fmt_instruction: str) -> str:
    priority_lines = "\n".join(f"- {p}" for p in priorities) if priorities else "- General quality"
    tech_lines     = "\n".join(f"- {t.strip()}" for t in techs.split(",") if t.strip())

    return f"""# Agent: {rol}

## Rol
Sos {rol}. Tu objetivo es ayudar al equipo a tomar decisiones técnicas sólidas dentro de tu especialidad.

## Prioridades (de mayor a menor importancia)
{priority_lines}

## Stack y tecnologías
{tech_lines if tech_lines else "- General (no stack específico)"}

## Instrucciones de respuesta
{fmt_instruction}

## Restricciones
- Limitá tus respuestas al área de tu especialidad.
- Si algo está fuera de tu dominio, decilo explícitamente.
- No asumas contexto que no se te dió. Pedí aclaraciones si es necesario.
- Priorizá soluciones simples y mantenibles salvo que se requiera otra cosa.
"""


def create_custom_agent(agents_dir: Path) -> tuple[str, Path]:
    """
    Wizard de 4 preguntas. Retorna (slug_name, path_al_archivo).
    El caller decide si activarlo para el proyecto.
    """
    console.print()
    console.print(Panel(
        "[bold cyan]🔮 Crear Agente Personalizado[/bold cyan]\n"
        "[dim]Respondé 4 preguntas y PISKU genera el .md[/dim]",
        border_style="cyan",
    ))

    # ── Pregunta 1: Rol ───────────────────────────────────────────────────────
    console.print("\n[bold]1/4 — ¿Qué rol va a tener este agente?[/bold]")
    console.print("[dim]Ej: Arquitecto Cloud, Especialista en testing, Code Reviewer senior[/dim]")
    while True:
        rol = Prompt.ask("Rol").strip()
        if len(rol) >= 3:
            break
        console.print("[red]Ingresá al menos 3 caracteres[/red]")

    # ── Pregunta 2: Prioridades ───────────────────────────────────────────────
    console.print("\n[bold]2/4 — ¿Qué debe priorizar? [/bold][dim](comma-separated)[/dim]")
    for i, (label, _) in enumerate(PRIORITIES, 1):
        console.print(f"  [dim]{i}.[/dim] {label}")
    while True:
        raw = Prompt.ask("Selección", default="1,2").strip()
        chosen_priorities = _parse_multi_selection(raw, PRIORITIES)
        if chosen_priorities:
            labels = [l for l, _ in chosen_priorities]
            console.print(f"  [green]✓[/green] {', '.join(labels)}")
            break
        console.print("[red]Seleccioná al menos uno[/red]")

    # ── Pregunta 3: Tecnologías ───────────────────────────────────────────────
    console.print("\n[bold]3/4 — ¿En qué tecnologías se especializa?[/bold]")
    console.print("[dim]Ej: AWS, Kubernetes, Terraform  /  React, TypeScript, Tailwind[/dim]")
    techs = Prompt.ask("Tecnologías (comma-separated)").strip()
    if not techs:
        techs = "General"

    # ── Pregunta 4: Formato ───────────────────────────────────────────────────
    console.print("\n[bold]4/4 — ¿Qué formato de respuesta preferís?[/bold]")
    for i, (label, _) in enumerate(FORMATS, 1):
        console.print(f"  [dim]{i}.[/dim] {label}")
    while True:
        raw = Prompt.ask("Selección", default="1").strip()
        try:
            idx = int(raw) - 1
            _, fmt_instruction = FORMATS[idx]
            console.print(f"  [green]✓[/green] {FORMATS[idx][0]}")
            break
        except (ValueError, IndexError):
            console.print("[red]Ingresá 1, 2 o 3[/red]")

    # ── Generar y guardar ─────────────────────────────────────────────────────
    priority_labels = [l for l, _ in chosen_priorities]
    content = _generate_agent_md(rol, priority_labels, techs, fmt_instruction)

    slug      = _slugify(rol)
    dest      = agents_dir / f"{slug}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")

    console.print()
    console.print(f"  [green]✅ Agente creado:[/green] [dim]{dest}[/dim]")

    return slug, dest
