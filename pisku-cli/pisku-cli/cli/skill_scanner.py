"""
PISKU Skill Scanner — encuentra y parsea SKILL.md en todos los directorios
de AI coding tools instalados en el sistema.

Soporta: Claude Code, OpenCode, GitHub Copilot, Codex, Cursor, Cline, Windsurf, Roo, Zed
"""
from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass, field


# ── Directorios que cada tool usa para sus skills ─────────────────────────────
# Cada entry: (tool_key, [lista de paths a escanear])
# Orden: global primero, luego project-level

def _tool_dirs() -> list[tuple[str, list[Path]]]:
    home = Path.home()
    cwd  = Path.cwd()
    return [
        ("claude-code", [
            home / ".claude" / "skills",
            cwd  / ".claude" / "skills",
        ]),
        ("opencode", [
            home / ".opencode" / "skills",
            cwd  / ".opencode" / "skills",
        ]),
        ("copilot", [
            home / ".github" / "skills",
            cwd  / ".github"  / "skills",
        ]),
        ("codex", [
            home / ".codex" / "skills",
            cwd  / ".codex" / "skills",
        ]),
        ("cursor", [
            cwd / ".cursor" / "skills",
        ]),
        ("cline", [
            cwd / ".clinerules" / "skills",
        ]),
        ("windsurf", [
            cwd / ".windsurfrules" / "skills",
        ]),
        ("roo", [
            cwd / ".roo" / "skills",
        ]),
        ("zed", [
            home / ".zed" / "skills",
            cwd  / ".zed" / "skills",
        ]),
    ]


# ── Skill dataclass ───────────────────────────────────────────────────────────

@dataclass
class Skill:
    name:        str
    description: str
    path:        Path
    tool:        str          # which tool owns this install
    scope:       str          # "global" | "project"
    raw:         str          # full file content
    # derived fields (populated by scanner)
    char_count:  int   = 0
    word_count:  int   = 0
    body_tokens: int   = 0    # estimated tokens in body (for cost calc)

    def __post_init__(self):
        self.char_count  = len(self.description)
        self.word_count  = len(self.description.split())
        # rough token estimate for body: chars / 4
        body = _extract_body(self.raw)
        self.body_tokens = max(1, len(body) // 4)

    @property
    def metadata_tokens(self) -> int:
        """Tokens loaded every session (name + description only)."""
        return max(10, (len(self.name) + len(self.description)) // 4)

    @property
    def slug(self) -> str:
        return self.name.lower().replace(" ", "-")


# ── Parsing ───────────────────────────────────────────────────────────────────

def _parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter fields as a flat dict."""
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    fm = content[3:end]
    result: dict = {}
    for line in fm.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip().lower()] = val.strip().strip("\"'")
    return result


def _extract_body(content: str) -> str:
    """Return everything after the closing --- of frontmatter."""
    if not content.startswith("---"):
        return content
    end = content.find("---", 3)
    if end == -1:
        return content
    return content[end + 3:].strip()


def _parse_skill_file(path: Path, tool: str, scope: str) -> Skill | None:
    """Parse a single SKILL.md file into a Skill object."""
    try:
        raw  = path.read_text(encoding="utf-8", errors="replace")
        meta = _parse_frontmatter(raw)

        # name: prefer frontmatter, fall back to parent directory name
        name = meta.get("name") or path.parent.name or path.stem
        desc = meta.get("description", "").strip()

        if not desc:
            # Try to find description in body (first non-heading line)
            for line in _extract_body(raw).splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    desc = line[:200]
                    break

        return Skill(
            name=name,
            description=desc,
            path=path,
            tool=tool,
            scope=scope,
            raw=raw,
        )
    except Exception:
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def scan_all_skills(extra_dirs: list[Path] | None = None) -> list[Skill]:
    """
    Scan all known tool directories and return deduplicated list of Skill objects.
    extra_dirs: additional paths to scan (for testing or custom setups).
    """
    skills:     list[Skill] = []
    seen_paths: set[Path]   = set()   # resolved paths to avoid symlink duplicates
    home = Path.home()

    all_dirs: list[tuple[str, Path, str]] = []  # (tool, path, scope)

    for tool, paths in _tool_dirs():
        for p in paths:
            scope = "global" if p.is_relative_to(home) else "project"
            all_dirs.append((tool, p, scope))

    if extra_dirs:
        for p in extra_dirs:
            all_dirs.append(("custom", p, "custom"))

    for tool, base_dir, scope in all_dirs:
        if not base_dir.exists():
            continue
        # Each skill lives in its own subdirectory containing SKILL.md
        for skill_file in sorted(base_dir.rglob("SKILL.md")):
            resolved = skill_file.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)

            skill = _parse_skill_file(skill_file, tool, scope)
            if skill:
                skills.append(skill)

    return skills


def find_skill(name: str, skills: list[Skill]) -> Skill | None:
    """Find a skill by name (case-insensitive, slug-aware)."""
    slug = name.lower().replace(" ", "-")
    for s in skills:
        if s.slug == slug or s.name.lower() == name.lower():
            return s
    return None


def update_description(skill: Skill, new_description: str) -> bool:
    """
    Rewrite the description field in the SKILL.md file in-place.
    Returns True on success.
    """
    try:
        content = skill.path.read_text(encoding="utf-8")

        if "description:" in content and content.startswith("---"):
            # Replace the existing description line
            lines   = content.splitlines(keepends=True)
            new_lines = []
            replaced  = False
            for line in lines:
                if not replaced and re.match(r"^description\s*:", line):
                    new_lines.append(f'description: "{new_description}"\n')
                    replaced = True
                else:
                    new_lines.append(line)
            if not replaced:
                # Insert after opening ---
                for i, line in enumerate(new_lines):
                    if i > 0 and line.strip() == "---":
                        new_lines.insert(i, f'description: "{new_description}"\n')
                        break
            skill.path.write_text("".join(new_lines), encoding="utf-8")
        else:
            # No frontmatter at all — prepend one
            new_content = (
                f"---\n"
                f"name: {skill.name}\n"
                f'description: "{new_description}"\n'
                f"---\n\n"
                + content
            )
            skill.path.write_text(new_content, encoding="utf-8")

        return True
    except Exception:
        return False
