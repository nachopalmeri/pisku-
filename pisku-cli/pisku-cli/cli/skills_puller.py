"""
PISKU Skills Puller — instala skills desde el ecosistema skills.sh (GitHub repos).

Flujo:
  1. Fetch del árbol del repo via GitHub API (sin auth para repos públicos)
  2. Lista todos los SKILL.md encontrados
  3. Muestra preview de cada skill (frontmatter + primeras líneas)
  4. Pide confirmación explícita antes de instalar (seguridad)
  5. Guarda en ~/.pisku/skills/<category>/<name>.md

Seguridad:
  Las skills son instrucciones en texto plano que el LLM va a seguir.
  Una skill de terceros podría contener prompt injection.
  Por eso SIEMPRE se muestra el contenido antes de instalar.
"""
import os
import re
import json
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich import box

console = Console()

GITHUB_API    = "https://api.github.com"

# Path to bundled system skills (installed with the package)
_PACKAGE_ROOT = Path(__file__).parent.parent
BUNDLED_SKILLS_DIR = _PACKAGE_ROOT / "skills"


class OfflineError(RuntimeError):
    """Raised when GitHub is unreachable — triggers fallback to bundled skills."""
    pass
GITHUB_RAW    = "https://raw.githubusercontent.com"
SKILLS_SH_URL = "https://skills.sh"

CATEGORY_HINTS: dict[str, str] = {
    "react":       "frontend",
    "vue":         "frontend",
    "angular":     "frontend",
    "css":         "frontend",
    "html":        "frontend",
    "next":        "frontend",
    "svelte":      "frontend",
    "typescript":  "frontend",
    "frontend":    "frontend",
    "design":      "frontend",
    "ui":          "frontend",

    "python":      "backend",
    "fastapi":     "backend",
    "django":      "backend",
    "flask":       "backend",
    "node":        "backend",
    "express":     "backend",
    "api":         "backend",
    "rest":        "backend",
    "graphql":     "backend",
    "backend":     "backend",
    "server":      "backend",
    "supabase":    "backend",

    "postgres":    "backend",
    "mysql":       "backend",
    "sqlite":      "backend",
    "mongo":       "backend",
    "database":    "backend",
    "sql":         "backend",
    "redis":       "backend",
    "orm":         "backend",

    "docker":      "devops",
    "kubernetes":  "devops",
    "ci":          "devops",
    "cd":          "devops",
    "github":      "devops",
    "gitlab":      "devops",
    "deploy":      "devops",
    "terraform":   "devops",
    "devops":      "devops",
    "aws":         "devops",
    "azure":       "devops",
    "gcp":         "devops",
    "cloud":       "devops",

    "solidity":    "web3",
    "ethereum":    "web3",
    "web3":        "web3",
    "blockchain":  "web3",
    "smart":       "web3",
    "nft":         "web3",

    "test":        "testing",
    "pytest":      "testing",
    "jest":        "testing",
    "vitest":      "testing",
    "coverage":    "testing",
    "qa":          "testing",
    "spec":        "testing",
}

VALID_CATEGORIES = ["backend", "frontend", "web3", "devops", "testing"]

GITHUB_TOKEN_ENV = "GITHUB_TOKEN"   # Optional — raises rate limit 60→5000 req/hr

# Keywords that indicate potentially dangerous skill content (prompt injection / code execution)
RISK_KEYWORDS: list[tuple[str, str]] = [
    ("eval(",         "Code execution via eval()"),
    ("exec(",         "Code execution via exec()"),
    ("os.system(",    "Shell command execution"),
    ("subprocess.",   "Subprocess execution"),
    ("__import__(",   "Dynamic import"),
    ("open(",         "File system access"),
    ("http://",       "Unencrypted HTTP URL"),
    ("curl ",         "Shell curl command"),
    ("wget ",         "Shell wget command"),
    ("rm -",          "File deletion command"),
    ("ignore all",    "Possible prompt injection"),
    ("ignore previous", "Possible prompt injection"),
    ("disregard",     "Possible prompt injection"),
    ("forget your",   "Possible prompt injection"),
    ("you are now",   "Persona hijack attempt"),
]


class RemoteSkill:
    """Represents a skill found in a remote GitHub repo."""
    def __init__(
        self,
        name:        str,
        description: str,
        repo:        str,      # "owner/repo"
        path:        str,      # path to SKILL.md in repo
        branch:      str,
        content:     str,
    ):
        self.name        = name
        self.description = description
        self.repo        = repo
        self.path        = path
        self.branch      = branch
        self.content     = content
        self.source_url  = f"{SKILLS_SH_URL}/{repo}/{name}"

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode()).hexdigest()[:12]

    def guess_category(self) -> str:
        text = (self.name + " " + self.description + " " + self.path).lower()
        for keyword, cat in CATEGORY_HINTS.items():
            if keyword in text:
                return cat
        return "backend"   # safe default

    def to_pisku_md(self) -> str:
        """
        Strip YAML frontmatter and add a PISKU source header.
        The resulting .md is what PISKU injects as context for the LLM.
        """
        body = _strip_frontmatter(self.content)
        header = (
            f"<!-- pisku:source repo={self.repo} path={self.path} "
            f"hash={self.content_hash} fetched={datetime.utcnow().date()} -->\n\n"
        )
        return header + body.strip() + "\n"


# ── Frontmatter helpers ───────────────────────────────────────────────────────

def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parse YAML frontmatter from a SKILL.md file.
    Returns (metadata_dict, body_without_frontmatter).
    """
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    fm_text = parts[1].strip()
    body    = parts[2]

    meta: dict = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip().lower()] = val.strip().strip('"').strip("'")
    return meta, body


def _strip_frontmatter(content: str) -> str:
    _, body = _parse_frontmatter(content)
    return body


# ── GitHub API ────────────────────────────────────────────────────────────────

def _github_headers() -> dict:
    headers = {
        "Accept":     "application/vnd.github+json",
        "User-Agent": "pisku-cli/0.2.1",
    }
    token = os.environ.get(GITHUB_TOKEN_ENV, "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _resolve_default_branch(owner: str, repo: str, timeout: float) -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    r = httpx.get(url, headers=_github_headers(), timeout=timeout)
    r.raise_for_status()
    return r.json().get("default_branch", "main")


def _fetch_repo_tree(owner: str, repo: str, branch: str, timeout: float) -> list[dict]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    r = httpx.get(url, headers=_github_headers(), timeout=timeout)
    _check_rate_limit(r)
    r.raise_for_status()
    data = r.json()
    if data.get("truncated"):
        console.print("[yellow]⚠️  Repo tree truncated (>100k files). Some skills may be missing.[/yellow]")
    return data.get("tree", [])


def _check_rate_limit(response: httpx.Response) -> None:
    """Raise a clear RuntimeError if GitHub rate limit is exceeded."""
    if response.status_code == 403:
        body = response.text.lower()
        if "rate limit" in body or "api rate limit exceeded" in body:
            remaining = response.headers.get("x-ratelimit-remaining", "0")
            reset_ts   = response.headers.get("x-ratelimit-reset", "")
            hint = ""
            if reset_ts:
                try:
                    from datetime import datetime
                    reset_dt = datetime.fromtimestamp(int(reset_ts))
                    hint = f"\n  Reset en: {reset_dt.strftime('%H:%M:%S')}"
                except Exception:
                    pass
            raise RuntimeError(
                f"GitHub API rate limit alcanzado (remaining: {remaining}).{hint}\n"
                f"  Solución: configurá tu token para 5000 req/hora:\n"
                f"  → Windows: setx GITHUB_TOKEN ghp_tu_token\n"
                f"  → Linux/Mac: export GITHUB_TOKEN=ghp_tu_token"
            )


def _fetch_raw_file(owner: str, repo: str, branch: str, path: str, timeout: float) -> str:
    url = f"{GITHUB_RAW}/{owner}/{repo}/{branch}/{path}"
    r = httpx.get(url, headers=_github_headers(), timeout=timeout)
    r.raise_for_status()
    return r.text


def _find_skill_paths(tree: list[dict]) -> list[str]:
    """Return paths of all SKILL.md files in the repo tree."""
    return [
        item["path"]
        for item in tree
        if item["type"] == "blob"
        and item["path"].endswith("SKILL.md")
        # Exclude internal/template skills
        and not any(seg.startswith(".") for seg in item["path"].split("/"))
    ]


# ── Display ───────────────────────────────────────────────────────────────────

def scan_security_risks(content: str) -> list[tuple[str, str]]:
    """
    Scan skill content for potentially dangerous patterns.
    Returns list of (matched_keyword, description) tuples.
    Content is lowercased for matching but original is preserved for display.
    """
    lower = content.lower()
    found = []
    for keyword, description in RISK_KEYWORDS:
        if keyword.lower() in lower:
            found.append((keyword, description))
    return found


def _display_skill_table(
    skills: list[RemoteSkill],
    recommended: set[str] | None = None,
) -> None:
    rec = recommended or set()
    table = Table(
        title=f"🌐 Skills disponibles ({len(skills)} encontradas)",
        box=box.ROUNDED,
        border_style="cyan",
    )
    table.add_column("#",    style="dim",        width=4)
    table.add_column("",    width=2)   # ★ column
    table.add_column("Name", style="bold white")
    table.add_column("Category", style="cyan")
    table.add_column("Description", style="dim")

    for i, s in enumerate(skills, 1):
        star = "[green]★[/green]" if s.name in rec else ""
        table.add_row(
            str(i),
            star,
            s.name,
            s.guess_category(),
            s.description[:55] + ("…" if len(s.description) > 55 else ""),
        )
    console.print(table)

    if rec:
        rec_names = [s.name for s in skills if s.name in rec]
        if rec_names:
            console.print(
                f"  [green]★[/green] [dim]Recomendadas para tu perfil:[/dim] "
                f"[green]{', '.join(rec_names)}[/green]  [dim](escribí 'rec')[/dim]"
            )


def _display_security_warning(skill: RemoteSkill) -> None:
    risks = scan_security_risks(skill.content)

    risk_lines = ""
    if risks:
        risk_lines = "\n\n[bold red]🚨 Keywords de riesgo detectadas:[/bold red]\n"
        for kw, desc in risks:
            risk_lines += f"  [red]• {kw}[/red]  [dim]{desc}[/dim]\n"
        risk_lines += "\n[red]REVISÁ cuidadosamente antes de instalar.[/red]"
    else:
        risk_lines = "\n\n[green]✓ Sin keywords de riesgo detectadas.[/green]"

    border = "red" if risks else "yellow"
    console.print()
    console.print(Panel(
        f"[bold yellow]⚠️  AVISO DE SEGURIDAD[/bold yellow]\n\n"
        f"Estás a punto de instalar una skill de terceros:\n"
        f"  Repo   : [cyan]{skill.repo}[/cyan]\n"
        f"  Path   : [dim]{skill.path}[/dim]\n"
        f"  Hash   : [dim]{skill.content_hash}[/dim]"
        f"{risk_lines}\n\n"
        f"[dim]Las skills son instrucciones que el LLM va a seguir.[/dim]",
        border_style=border,
    ))


def _display_skill_preview(skill: RemoteSkill) -> None:
    lines = skill.content.splitlines()[:40]
    preview = "\n".join(lines)
    console.print()
    console.print(Panel(
        f"[bold]Preview:[/bold] {skill.name}\n[dim]{skill.path}[/dim]",
        border_style="dim",
    ))
    console.print(Syntax(preview, "markdown", theme="monokai", line_numbers=False))
    if len(skill.content.splitlines()) > 40:
        console.print(f"  [dim]… ({len(skill.content.splitlines())} líneas en total)[/dim]")


# ── Main public interface ─────────────────────────────────────────────────────

class SkillsPuller:
    def __init__(
        self,
        user_skills_dir: Path,
        timeout: float = 15.0,
        recommended_skill_names: Optional[list[str]] = None,
    ):
        self.user_skills_dir = user_skills_dir
        self.timeout = timeout
        self.recommended = set(recommended_skill_names or [])  # names to mark with ★

    # ── Fetch ─────────────────────────────────────────────────────────────────

    def fetch_available(
        self,
        source: str,           # "owner/repo" or full GitHub URL
        skill_name: Optional[str] = None,   # filter to specific skill
    ) -> list[RemoteSkill]:
        """
        Fetch available skills from a GitHub repo.
        Returns list of RemoteSkill objects (content fetched, not yet installed).
        """
        owner, repo = _parse_source(source)
        console.print(f"\n[cyan]🔍 Buscando skills en[/cyan] [bold]{owner}/{repo}[/bold]...")

        try:
            branch = _resolve_default_branch(owner, repo, self.timeout)
            tree   = _fetch_repo_tree(owner, repo, branch, self.timeout)
        except httpx.ConnectError:
            raise OfflineError("Sin conexión a GitHub.")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise RuntimeError(f"Repo '{owner}/{repo}' no encontrado en GitHub.")
            raise RuntimeError(f"GitHub respondió {e.response.status_code}.")

        skill_paths = _find_skill_paths(tree)
        if not skill_paths:
            raise RuntimeError(
                f"No se encontraron archivos SKILL.md en '{owner}/{repo}'.\n"
                f"Asegurate de que el repo siga el formato de skills.sh."
            )

        # Filter by name if requested
        if skill_name:
            slug = skill_name.lower().replace(" ", "-")
            skill_paths = [
                p for p in skill_paths
                if Path(p).parent.name.lower() == slug
                or Path(p).stem.lower() == slug
            ]
            if not skill_paths:
                raise RuntimeError(
                    f"Skill '{skill_name}' no encontrada en '{owner}/{repo}'."
                )

        skills: list[RemoteSkill] = []
        with console.status(f"[dim]Descargando {len(skill_paths)} skill(s)…[/dim]"):
            for path in skill_paths:
                try:
                    content = _fetch_raw_file(owner, repo, branch, path, self.timeout)
                    meta, _ = _parse_frontmatter(content)
                    name = meta.get("name") or Path(path).parent.name or Path(path).stem
                    desc = meta.get("description") or ""
                    skills.append(RemoteSkill(
                        name=name,
                        description=desc,
                        repo=f"{owner}/{repo}",
                        path=path,
                        branch=branch,
                        content=content,
                    ))
                except Exception:
                    # Skip skills that fail to fetch — don't abort entire operation
                    pass

        console.print(f"  [green]✓[/green] {len(skills)} skill(s) encontradas en [cyan]{owner}/{repo}[/cyan]")
        return skills

    # ── Interactive install ───────────────────────────────────────────────────

    def interactive_install(self, source: str, skill_name: Optional[str] = None) -> list[Path]:
        """
        Full interactive flow:
          1. Fetch available skills
          2. Show table → user selects
          3. For each selected: security warning + preview + confirm
          4. Install to ~/.pisku/skills/
        Returns list of installed paths.
        """
        try:
            skills = self.fetch_available(source, skill_name)
        except RuntimeError as e:
            console.print(f"[red]❌ {e}[/red]")
            return []

        if not skills:
            console.print("[yellow]No se encontraron skills.[/yellow]")
            return []

        # If only 1 skill (explicit --skill flag), skip the selection table
        if len(skills) == 1:
            to_install = skills
        else:
            _display_skill_table(skills, recommended=self.recommended)
            console.print()

            # Default to "rec" if there are recommendations, else blank
            has_recs = any(s.name in self.recommended for s in skills)
            default_sel = "rec" if has_recs else ""
            raw = Prompt.ask(
                "[bold]Seleccioná skills[/bold] [dim](ej: 1,3  1-5  all  rec)[/dim]",
                default=default_sel,
            ).strip()

            if not raw:
                console.print("[yellow]Nada seleccionado.[/yellow]")
                return []

            # "rec" auto-selects recommended skills
            if raw.lower() == "rec":
                to_install = [s for s in skills if s.name in self.recommended]
                if not to_install:
                    console.print("[yellow]No hay skills recomendadas en este repo. Seleccioná manualmente.[/yellow]")
                    return []
                console.print(
                    f"  [green]★ Auto-seleccionadas {len(to_install)} skill(s) recomendadas[/green]"
                )
            else:
                to_install = _parse_selection(raw, skills)
                if not to_install:
                    console.print("[red]Selección inválida.[/red]")
                    return []

        installed: list[Path] = []
        for skill in to_install:
            path = self._install_one(skill)
            if path:
                installed.append(path)

        if installed:
            console.print()
            console.print(Panel(
                f"[bold green]✅ {len(installed)} skill(s) instaladas[/bold green]\n"
                + "\n".join(f"  • [cyan]{p.name}[/cyan]  [dim]{p.parent}[/dim]" for p in installed),
                border_style="green",
            ))

        return installed

    def _install_one(self, skill: RemoteSkill) -> Optional[Path]:
        """Show security warning, preview, confirm, and save."""
        _display_security_warning(skill)
        _display_skill_preview(skill)

        console.print()
        ok = Confirm.ask(
            f"[bold]¿Instalar '{skill.name}'?[/bold] [dim](revisá el contenido de arriba)[/dim]",
            default=False,   # default NO — usuario debe confirmar explícitamente
        )
        if not ok:
            console.print(f"  [dim]Skipped: {skill.name}[/dim]")
            return None

        # Choose category
        suggested = skill.guess_category()
        console.print(
            f"\n  Categoría sugerida: [cyan]{suggested}[/cyan]  "
            f"[dim](opciones: {', '.join(VALID_CATEGORIES)})[/dim]"
        )
        category = Prompt.ask("  Categoría", default=suggested).strip().lower()
        if category not in VALID_CATEGORIES:
            console.print(f"  [yellow]Categoría inválida, usando '{suggested}'[/yellow]")
            category = suggested

        dest = self.user_skills_dir / category / f"{_safe_name(skill.name)}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(skill.to_pisku_md(), encoding="utf-8")
        console.print(f"  [green]✓[/green] Instalada en [dim]{dest}[/dim]")
        return dest

    def _fallback_bundled_list(self) -> list[RemoteSkill]:
        """
        When GitHub is unreachable, return bundled system skills as RemoteSkill objects
        so the user can still install them into ~/.pisku/skills/ (user-editable copy).
        """
        skills: list[RemoteSkill] = []
        if not BUNDLED_SKILLS_DIR.exists():
            return skills

        for skill_file in sorted(BUNDLED_SKILLS_DIR.rglob("*.md")):
            if skill_file.parent.name == "agents":
                continue   # agents are not installable as skills
            try:
                content_text = skill_file.read_text(encoding="utf-8")
                meta, _      = _parse_frontmatter(content_text)
                name         = meta.get("name") or skill_file.stem
                desc         = meta.get("description") or f"Bundled skill from {skill_file.parent.name}"
                skills.append(RemoteSkill(
                    name=name,
                    description=desc,
                    repo="pisku/bundled",
                    path=str(skill_file.relative_to(BUNDLED_SKILLS_DIR.parent)),
                    branch="local",
                    content=content_text,
                ))
            except Exception:
                continue
        return skills

    # ── Non-interactive (for scripting / --yes flag) ──────────────────────────

    def install_direct(
        self,
        source: str,
        skill_name: str,
        category: Optional[str] = None,
        yes: bool = False,
    ) -> Optional[Path]:
        """
        Install a specific skill non-interactively.
        Always shows the content unless yes=True.
        Returns installed path or None.
        """
        try:
            skills = self.fetch_available(source, skill_name)
        except RuntimeError as e:
            console.print(f"[red]❌ {e}[/red]")
            return None

        if not skills:
            console.print(f"[red]Skill '{skill_name}' no encontrada.[/red]")
            return None

        skill = skills[0]
        cat   = category or skill.guess_category()

        if not yes:
            _display_security_warning(skill)
            _display_skill_preview(skill)
            console.print()
            if not Confirm.ask(f"[bold]¿Instalar '{skill.name}'?[/bold]", default=False):
                return None

        if cat not in VALID_CATEGORIES:
            cat = skill.guess_category()

        dest = self.user_skills_dir / cat / f"{_safe_name(skill.name)}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(skill.to_pisku_md(), encoding="utf-8")
        console.print(f"[green]✅ Instalada:[/green] {dest}")
        return dest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_source(source: str) -> tuple[str, str]:
    """
    Accepts:
      - "owner/repo"
      - "https://github.com/owner/repo"
      - "https://github.com/owner/repo/tree/main/subdir"
    Returns (owner, repo).
    """
    source = source.strip().rstrip("/")
    # Full URL
    if "github.com" in source:
        parts = source.split("github.com/")[-1].split("/")
        return parts[0], parts[1]
    # Short form
    if "/" in source:
        parts = source.split("/")
        return parts[0], parts[1]
    raise ValueError(f"Formato de fuente inválido: '{source}'. Usá 'owner/repo'.")


def _safe_name(name: str) -> str:
    """Convert skill name to filesystem-safe slug."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\-]", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "skill"


def _parse_selection(raw: str, skills: list[RemoteSkill]) -> list[RemoteSkill]:
    """Parse "1,3", "1-5", "all" into list of RemoteSkill objects."""
    if raw.lower() == "all":
        return skills

    indexed = {i + 1: s for i, s in enumerate(skills)}
    selected: list[RemoteSkill] = []
    try:
        for part in raw.replace(" ", "").split(","):
            if "-" in part:
                a, b = part.split("-", 1)
                for n in range(int(a), int(b) + 1):
                    if n in indexed and indexed[n] not in selected:
                        selected.append(indexed[n])
            else:
                n = int(part)
                if n in indexed and indexed[n] not in selected:
                    selected.append(indexed[n])
    except ValueError:
        return []
    return selected
