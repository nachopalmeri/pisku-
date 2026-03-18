"""
PISKU Tool Writer — escribe un manifest liviano al archivo que lee cada AI coding tool.

Qué escribe: ~20-30 líneas con nombres de skills, categorías, tamaños y extracto de agents.
Qué NO escribe: el contenido completo de las skills (eso queda en ~/.pisku/skills/).

Per-project config: cada proyecto tiene .pisku/config.json con tool elegida, skills y agents activos.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class ToolTarget:
    key:      str
    display:  str
    filename: str
    note:     str


TOOLS: list[ToolTarget] = [
    ToolTarget("opencode",    "OpenCode",           "AGENTS.md",                       "OpenCode lee AGENTS.md automáticamente al iniciar cada sesión."),
    ToolTarget("claude-code", "Claude Code",        "CLAUDE.md",                       "Claude Code lee CLAUDE.md al abrir el proyecto."),
    ToolTarget("cursor",      "Cursor",             ".cursor/rules",                   "Cursor aplica las rules automáticamente."),
    ToolTarget("cline",       "Cline (VS Code)",    ".clinerules",                     "Cline lee .clinerules en cada conversación nueva."),
    ToolTarget("windsurf",    "Windsurf",           ".windsurfrules",                  "Windsurf aplica las rules automáticamente."),
    ToolTarget("copilot",     "GitHub Copilot",     ".github/copilot-instructions.md", "Copilot incluye estas instrucciones en cada sugerencia."),
    ToolTarget("clipboard",   "Solo portapapeles",  "",                                "Pegá el contexto en tu AI con Ctrl+V."),
]

TOOL_BY_KEY: dict[str, ToolTarget] = {t.key: t for t in TOOLS}

PISKU_START = "<!-- pisku:start -->"
PISKU_END   = "<!-- pisku:end -->"
PROJECT_CONFIG_PATH = Path(".pisku") / "config.json"


# ── Per-project config ────────────────────────────────────────────────────────

def load_project_config(project_root: Path) -> dict:
    cfg_path = project_root / PROJECT_CONFIG_PATH
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def save_project_config(project_root: Path, config: dict) -> None:
    cfg_path = project_root / PROJECT_CONFIG_PATH
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Manifest builder ──────────────────────────────────────────────────────────

def build_manifest(
    project_name: str,
    tool_key: str,
    skills: list,
    agents: list,
    pisku_home: Path,
) -> str:
    """
    Build a lightweight manifest (~25 lines).
    Skills listed by name + category + size — NOT content.
    Agent instructions truncated to 120 chars.
    """
    now   = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# PISKU Context Manifest",
        f"Project  : {project_name}",
        f"Generated: {now}",
        f"Tool     : {tool_key}",
        "",
        "## Skills activas",
    ]

    for s in skills:
        size = f"{s.size_kb:.1f} KB" if hasattr(s, "size_kb") else "?"
        lines.append(f"- {s.name} [{s.category}] — {size}")

    lines += ["", "## Agents activos"]

    if agents:
        for a in agents:
            try:
                content = a.read()
                snippet = ""
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        snippet = stripped[:120]
                        break
                lines.append(f"- {a.name}: \"{snippet}{'...' if len(snippet) == 120 else ''}\"")
            except Exception:
                lines.append(f"- {a.name}")
    else:
        lines.append("- (sin agente)")

    lines += [
        "",
        "## Instrucciones para el LLM",
        "Usá SOLO las skills listadas arriba como referencia de patrones y convenciones.",
        f"Contenido completo en: {pisku_home / 'skills'}",
        "No asumas frameworks ni patrones que no estén en la lista.",
    ]

    return "\n".join(lines)


# ── Tool writer ───────────────────────────────────────────────────────────────

class ToolWriter:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def write(self, tool_key: str, manifest: str) -> tuple[bool, str]:
        tool = TOOL_BY_KEY.get(tool_key)
        if not tool:
            return False, f"Tool '{tool_key}' no reconocida."
        if not tool.filename:
            return True, tool.note

        target = self.project_root / tool.filename
        target.parent.mkdir(parents=True, exist_ok=True)
        pisku_block = f"{PISKU_START}\n{manifest.strip()}\n{PISKU_END}\n"

        if target.exists():
            existing = target.read_text(encoding="utf-8")
            if PISKU_START in existing:
                pattern = re.compile(
                    rf"{re.escape(PISKU_START)}.*?{re.escape(PISKU_END)}\n?",
                    re.DOTALL,
                )
                target.write_text(pattern.sub(pisku_block, existing), encoding="utf-8")
                return True, f"✅ Actualizado `{tool.filename}`  —  {tool.note}"
            else:
                target.write_text(existing.rstrip() + "\n\n" + pisku_block, encoding="utf-8")
                return True, f"✅ Agregado a `{tool.filename}` (contenido previo preservado)  —  {tool.note}"
        else:
            target.write_text(pisku_block, encoding="utf-8")
            return True, f"✅ Creado `{tool.filename}`  —  {tool.note}"

    def remove(self, tool_key: str) -> tuple[bool, str]:
        tool = TOOL_BY_KEY.get(tool_key)
        if not tool or not tool.filename:
            return False, "No se puede eliminar para esta tool."
        target = self.project_root / tool.filename
        if not target.exists():
            return False, f"`{tool.filename}` no existe."
        existing = target.read_text(encoding="utf-8")
        if PISKU_START not in existing:
            return False, f"No hay bloque PISKU en `{tool.filename}`."
        pattern = re.compile(
            rf"\n*{re.escape(PISKU_START)}.*?{re.escape(PISKU_END)}\n?",
            re.DOTALL,
        )
        cleaned = pattern.sub("", existing).strip()
        if cleaned:
            target.write_text(cleaned + "\n", encoding="utf-8")
        else:
            target.unlink()
        return True, f"✅ Bloque PISKU eliminado de `{tool.filename}`"


def detect_tools_in_project(project_root: Path) -> list[ToolTarget]:
    return [t for t in TOOLS if t.filename and (project_root / t.filename).exists()]


def tool_menu_choices() -> list[tuple[str, str]]:
    return [(t.display, t.key) for t in TOOLS]
