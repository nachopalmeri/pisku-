# Changelog

## [0.3.0] — 2026-03-17

### Producto redefinido

PISKU pasó de ser un "selector manual de skills" a un **auditor predictivo**.
El insight que cambió todo: las skills se activan automáticamente por matching
de descripción, no manualmente. El problema real es skills con descripciones
demasiado amplias que disparan en cualquier sesión.

### Nuevos comandos

- `pisku audit` — auditoría completa de skills instaladas. Detecta descripciones
  problemáticas (demasiado cortas, broad keywords, sin trigger patterns) y
  conflictos de keywords entre skills.

- `pisku for "<tarea>"` — predictor pre-sesión. Antes de abrir tu CLI, te dice
  qué skills van a disparar, cuáles podrían disparar por error, y el costo
  estimado en tokens. Copia al portapapeles con `--copy`.

- `pisku fix [skill]` — fixer interactivo. Pregunta para qué usás la skill y
  genera una descripción optimizada siguiendo la spec oficial de Agent Skills.

### Nuevos archivos

- `cli/skill_scanner.py` — escanea `~/.claude/skills/`, `~/.opencode/skills/`
  y 7 tools más. Parsea frontmatter YAML, calcula tokens de metadata y body.
- `cli/skill_auditor.py` — scoring de salud (0-100), detección de broad keywords,
  trigger patterns faltantes, y conflictos entre skills.
- `cli/session_predictor.py` — matching keyword-based entre tarea y descripciones.
  Clasifica en will_fire / might_fire / wont_fire con costo estimado.

### Tools soportadas

Claude Code, OpenCode, GitHub Copilot, Codex, Cursor, Cline, Windsurf, Roo, Zed.

---

## [0.2.1] — 2026-03-11

### Hotfixes

- `license_manager.py`: DEFAULT_SERVER apuntaba a localhost. Corregido a Railway.
- `stats_tracker.py`: get_active_projects() no tenía ventana de 30 días.
  Usuarios FREE quedaban bloqueados permanentemente tras la primera sesión.

---

## [0.2.0] — 2026-03-10

- Wizard de perfil (dev type, stack, AI preferida)
- Recommender con scoring por perfil
- Skills manager con ★ en recomendadas
- Agents manager (system + user, FREE cap 3)
- Context builder
- Skills puller desde GitHub / skills.sh con security scan
- 10 skills bundled, 5 agents bundled
