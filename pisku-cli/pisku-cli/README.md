# ⚡ PISKU

**Auditá tus AI skills antes de quemar tokens.**

Instalás 15 skills en Claude Code, OpenCode o cualquier AI coding tool. Cada sesión las carga todas. Una skill con descripción muy amplia dispara aunque no tenga nada que ver con lo que estás haciendo — eso son tokens tirados.

PISKU te dice qué va a pasar antes de que pase.

---

## Instalación

```bash
pip install pisku
```

Requiere Python 3.11+.

---

## Tres comandos

### `pisku audit`

Escaneá todas las skills instaladas en tu sistema.

```
⚡ PISKU Skill Audit — 12 skills instaladas
   Metadata fija por sesión: ~1,200 tokens

CRÍTICO (2)
  ❌ python-best-practices  "General Python patterns"
     → Keywords amplios: [general, patterns] → over-match garantizado
     → Falta 'Use when/for' — el agente no sabe cuándo activarla

  ❌ backend-utils  "Utilities for backend development"
     → Keywords amplios: [utilities]

ADVERTENCIA (1)
  ⚠️  postgresql-sqlalchemy  "Backend database patterns with SQLAlchemy"
     → Falta 'Use when/for'

CONFLICTOS (1)
  🔥 docker-ci-cd ↔ kubernetes-deploy
     Keywords superpuestos: containers, deployment, orchestration

SALUDABLES (8)
  ✅ solidity-base, remotion-patterns, html-css ...
```

### `pisku for "tarea"`

Antes de abrir tu CLI, predecí qué skills van a disparar.

```bash
pisku for "hacer una landing con Bootstrap"
pisku for "hacer una landing con Bootstrap" --copy
```

```
🔮 Predicción para: "hacer una landing con Bootstrap"

VAN A DISPARAR — certeza alta (2)
  ✅ /bootstrap5-dark   ~480 tokens
  ✅ /html-css          ~320 tokens

PODRÍAN DISPARAR — descripciones problemáticas (1)
  ⚡ python-best-practices  ~900 tokens de ruido potencial
     "General Python patterns" — broad, puede matchear "hacer"

💰 Costo estimado
   Metadata fija   : ~1,200 tokens
   Skills útiles   : ~800 tokens
   Ruido potencial : ~900 tokens

   Si fixeás python-best-practices → ahorrás ~900 tokens por sesión

┌─────────────────────────────────────────────────────┐
│ Activá estas skills: /bootstrap5-dark /html-css     │
│ Si se activa python-best-practices, ignorala        │
│                                                     │
│ Contexto: hacer una landing con Bootstrap           │
└─────────────────────────────────────────────────────┘
```

Pegá ese texto al inicio de tu sesión en OpenCode, Claude Code, etc.

### `pisku fix`

Fixer interactivo de descripciones.

```bash
pisku fix python-best-practices   # fix una skill específica
pisku fix                         # fix todas las problemáticas
```

```
🔧 Fixing: python-best-practices

  Descripción actual: "General Python patterns"

  Problemas:
  → Keywords amplios: [general, patterns]
  → Falta 'Use when/for'

  ¿Para qué la instalaste?
  > async/await patterns, type hints, module structure

  Descripción sugerida:
  "Async/await patterns, type hints y module structure.
   Use when writing Python async code, adding type annotations,
   or structuring Python modules."

  ¿Qué hacemos? [usar/editar/saltar]: usar
  ✅ Guardado.
```

---

## Bonus: instalar skills desde skills.sh

```bash
pisku skills pull vercel-labs/agent-skills
pisku skills pull vercel-labs/agent-skills --skill frontend-design
```

Después de instalar, corré `pisku audit` para verificar que las nuevas skills tienen descripciones bien formadas.

---

## Tools soportadas

PISKU escanea automáticamente los directorios de skills de:

| Tool | Directorio |
|------|-----------|
| Claude Code | `~/.claude/skills/` |
| OpenCode | `~/.opencode/skills/` |
| GitHub Copilot | `~/.github/skills/` |
| Codex | `~/.codex/skills/` |
| Cursor | `.cursor/skills/` |
| Cline | `.clinerules/skills/` |
| Windsurf | `.windsurfrules/skills/` |
| Roo | `.roo/skills/` |
| Zed | `~/.zed/skills/` |

---

## ¿Por qué importa la descripción?

Cada sesión carga el `name` + `description` de cada skill instalada (~100 tokens por skill). El cuerpo completo de la skill (hasta 5000 tokens) carga solo cuando el agente decide que es relevante — y esa decisión se basa 100% en la descripción.

Descripción amplia → skill dispara para todo → tokens tirados.
Descripción específica con "Use when..." → skill dispara solo cuando corresponde.

PISKU audita eso antes de que lo pagues.

---

## Requisitos

- Python 3.11+
- Al menos una AI coding tool con skills instaladas via `npx skills add`

---

## Links

- [skills.sh](https://skills.sh) — directorio de skills
- [agentskills.io/specification](https://agentskills.io/specification) — spec oficial
- [github.com/nachopalmeri/pisku](https://github.com/nachopalmeri/pisku)
