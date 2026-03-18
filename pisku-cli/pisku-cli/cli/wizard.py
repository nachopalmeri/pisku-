"""
PISKU Wizard — 3-step onboarding that saves a user profile
and drives skill recommendations.
"""
import json
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

console = Console()

PROFILE_FILE = Path.home() / ".pisku" / "profile.json"

DEV_TYPES = [
    ("Junior Backend",   "junior_backend"),
    ("Senior Fullstack", "senior_fullstack"),
    ("Web3 Developer",   "web3"),
    ("DevOps Engineer",  "devops"),
    ("Data Engineer",    "data"),
]

STACK_OPTIONS = [
    ("Python",      "python"),
    ("Node.js",     "nodejs"),
    ("Go",          "go"),
    ("PostgreSQL",  "postgresql"),
    ("MongoDB",     "mongodb"),
    ("Redis",       "redis"),
    ("Docker",      "docker"),
    ("React",       "react"),
    ("Solidity",    "solidity"),
    ("Supabase",    "supabase"),
    ("Django",      "django"),
    ("TypeScript",  "typescript"),
]

AI_OPTIONS = [
    ("Claude",       "claude"),
    ("GPT-4 / 4o",   "gpt4"),
    ("Gemini",       "gemini"),
    ("MiniMax",      "minimax"),
    ("Otro",         "other"),
]


def _print_numbered_menu(title: str, options: list[tuple[str, str]]) -> None:
    console.print(f"\n[bold violet]{title}[/bold violet]\n")
    for i, (label, _) in enumerate(options, 1):
        console.print(f"  [dim]{i:2d})[/dim] {label}")
    console.print()


def _parse_single(raw: str, options: list[tuple[str, str]]) -> str | None:
    try:
        n = int(raw.strip())
        if 1 <= n <= len(options):
            return options[n - 1][1]
    except ValueError:
        pass
    return None


def _parse_multi(raw: str, options: list[tuple[str, str]]) -> list[str]:
    selected = []
    for part in raw.split(","):
        key = _parse_single(part, options)
        if key and key not in selected:
            selected.append(key)
    return selected


def load_profile() -> dict | None:
    """Return saved profile or None if not yet set up."""
    if PROFILE_FILE.exists():
        try:
            return json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save_profile(profile: dict) -> None:
    PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_FILE.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")


def run_wizard(force: bool = False) -> dict:
    """
    Run the 3-step onboarding wizard.
    Returns the saved profile dict.
    If profile already exists and force=False, returns existing profile.
    """
    existing = load_profile()
    if existing and not force:
        return existing

    console.print()
    console.print(Panel(
        "[bold violet]🔮 PISKU Setup Wizard[/bold violet]\n"
        "[dim]Takes 30 seconds — sets up personalised skill recommendations[/dim]",
        border_style="violet",
    ))

    # ── Step 1: dev type ────────────────────────────────────────────
    _print_numbered_menu("Step 1/3 — ¿Qué tipo de dev sos?", DEV_TYPES)
    while True:
        raw = Prompt.ask("[bold]Selection[/bold]", default="1")
        dev_type = _parse_single(raw, DEV_TYPES)
        if dev_type:
            dev_label = next(l for l, k in DEV_TYPES if k == dev_type)
            console.print(f"  [green]✓[/green] {dev_label}")
            break
        console.print("  [red]Ingresá un número válido[/red]")

    # ── Step 2: stack ───────────────────────────────────────────────
    _print_numbered_menu("Step 2/3 — ¿Qué stack usás? [dim](comma-separated)[/dim]", STACK_OPTIONS)
    while True:
        raw = Prompt.ask("[bold]Selection[/bold]", default="1")
        stack = _parse_multi(raw, STACK_OPTIONS)
        if stack:
            labels = [l for l, k in STACK_OPTIONS if k in stack]
            console.print(f"  [green]✓[/green] {', '.join(labels)}")
            break
        console.print("  [red]Seleccioná al menos uno[/red]")

    # ── Step 3: primary AI ──────────────────────────────────────────
    _print_numbered_menu("Step 3/3 — ¿Qué IA usás principalmente?", AI_OPTIONS)
    while True:
        raw = Prompt.ask("[bold]Selection[/bold]", default="1")
        ai = _parse_single(raw, AI_OPTIONS)
        if ai:
            ai_label = next(l for l, k in AI_OPTIONS if k == ai)
            console.print(f"  [green]✓[/green] {ai_label}")
            break
        console.print("  [red]Ingresá un número válido[/red]")

    profile = {
        "dev_type": dev_type,
        "stack": stack,
        "ai": ai,
        "created_at": datetime.utcnow().isoformat(),
    }
    save_profile(profile)

    console.print()
    console.print(Panel(
        "[bold green]✅ Profile saved![/bold green]\n"
        f"[dim]~/.pisku/profile.json[/dim]\n\n"
        f"Dev type : [cyan]{dev_type}[/cyan]\n"
        f"Stack    : [cyan]{', '.join(stack)}[/cyan]\n"
        f"AI       : [cyan]{ai}[/cyan]",
        border_style="green",
    ))

    return profile
