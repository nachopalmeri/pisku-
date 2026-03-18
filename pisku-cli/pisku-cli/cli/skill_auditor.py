"""
PISKU Skill Auditor — scoring de salud de descripciones + detección de conflictos.

Basado en la spec oficial de Agent Skills (agentskills.io/specification):
- La descripción es el único mecanismo de activación automática
- "Use when/for" patterns son el estándar recomendado
- Descriptions amplias = over-matching = tokens quemados
- Keywords superpuestos entre skills = ambas disparan juntas
"""
from __future__ import annotations

from dataclasses import dataclass, field
from cli.skill_scanner import Skill


# ── Thresholds ────────────────────────────────────────────────────────────────

MIN_CHARS         = 60    # below this: too vague
MAX_CHARS         = 300   # above this: dilutes matching
IDEAL_MIN_CHARS   = 80
IDEAL_MAX_CHARS   = 200

CONFLICT_THRESHOLD = 2    # meaningful shared keywords = conflict


# ── Broad keywords que causan over-matching ───────────────────────────────────

BROAD_KEYWORDS: set[str] = {
    "general", "utilities", "utility", "utils", "common", "basic",
    "standard", "patterns", "best", "practices", "helper", "helpers",
    "misc", "miscellaneous", "various", "all", "every", "any",
    "coding", "development", "programming",
}

# ── Trigger patterns recomendados por la spec ─────────────────────────────────

TRIGGER_PATTERNS: list[str] = [
    "use when", "use for", "trigger on", "activate when",
    "only for", "specific to", "specialized in",
    "when working with", "when building", "when writing",
    "for working", "for building", "for creating",
]

# ── Stopwords que NO cuentan como keywords significativos ─────────────────────

STOPWORDS: set[str] = {
    "the", "a", "an", "and", "or", "for", "when", "use", "to", "in",
    "with", "of", "on", "at", "by", "from", "as", "is", "are", "be",
    "this", "that", "it", "its", "you", "your", "i", "my", "our",
    "can", "will", "should", "may", "do", "does", "if", "then",
    "all", "any", "each", "every", "how", "what", "which", "who",
    "not", "but", "also", "more", "than", "too", "very",
}


# ── Result dataclasses ────────────────────────────────────────────────────────

@dataclass
class HealthIssue:
    severity: str    # "critical" | "warning" | "info"
    message:  str
    fix_hint: str = ""


@dataclass
class SkillHealth:
    skill:    Skill
    score:    int                      # 0-100
    issues:   list[HealthIssue] = field(default_factory=list)

    @property
    def level(self) -> str:
        if self.score < 40:   return "critical"
        if self.score < 70:   return "warning"
        return "healthy"


@dataclass
class Conflict:
    skill_a:          Skill
    skill_b:          Skill
    shared_keywords:  list[str]


@dataclass
class AuditReport:
    skills:    list[SkillHealth]
    conflicts: list[Conflict]

    @property
    def critical(self) -> list[SkillHealth]:
        return [s for s in self.skills if s.level == "critical"]

    @property
    def warning(self) -> list[SkillHealth]:
        return [s for s in self.skills if s.level == "warning"]

    @property
    def healthy(self) -> list[SkillHealth]:
        return [s for s in self.skills if s.level == "healthy"]

    @property
    def total_metadata_tokens(self) -> int:
        return sum(s.skill.metadata_tokens for s in self.skills)

    @property
    def savings_if_fixed(self) -> int:
        """Estimated token waste per session from broad/conflicting skills."""
        waste = 0
        for sh in self.skills:
            if sh.level in ("critical", "warning"):
                waste += sh.skill.body_tokens
        return waste


# ── Scoring ───────────────────────────────────────────────────────────────────

def _meaningful_words(text: str) -> set[str]:
    """Extract meaningful lowercase words (no stopwords, no punctuation)."""
    words = set()
    for w in text.lower().split():
        w = w.strip(".,;:!?\"'()[]{}/-")
        if w and w not in STOPWORDS and len(w) > 2:
            words.add(w)
    return words


def score_skill(skill: Skill) -> SkillHealth:
    score  = 100
    issues: list[HealthIssue] = []
    desc   = skill.description
    desc_l = desc.lower()

    # ── No description at all ────────────────────────────────────────
    if not desc.strip():
        return SkillHealth(
            skill=skill,
            score=0,
            issues=[HealthIssue(
                "critical",
                "Sin descripción — la skill NUNCA va a activarse",
                "Agregá una descripción con 'Use when/for ...'",
            )],
        )

    # ── Too short ────────────────────────────────────────────────────
    if len(desc) < MIN_CHARS:
        score -= 30
        issues.append(HealthIssue(
            "critical",
            f"Muy corta ({len(desc)} chars, mínimo {MIN_CHARS})",
            "Describí qué hace la skill Y cuándo activarla",
        ))
    elif len(desc) < IDEAL_MIN_CHARS:
        score -= 10
        issues.append(HealthIssue(
            "warning",
            f"Corta ({len(desc)} chars) — puede no activarse cuando deberías",
            "Agregá ejemplos de cuándo usarla",
        ))

    # ── Too long ─────────────────────────────────────────────────────
    if len(desc) > MAX_CHARS:
        score -= 20
        issues.append(HealthIssue(
            "warning",
            f"Muy larga ({len(desc)} chars, máximo recomendado {MAX_CHARS})",
            "Acortá — las descripciones largas diluyen el matching",
        ))

    # ── Broad keywords ───────────────────────────────────────────────
    words = _meaningful_words(desc)
    found_broad = words & BROAD_KEYWORDS
    if found_broad:
        score -= 25
        kws = ", ".join(sorted(found_broad))
        issues.append(HealthIssue(
            "critical",
            f"Keywords amplios: [{kws}] → over-match garantizado",
            f"Reemplazá por keywords específicos de la skill",
        ))

    # ── Missing trigger pattern ──────────────────────────────────────
    has_trigger = any(p in desc_l for p in TRIGGER_PATTERNS)
    if not has_trigger:
        score -= 20
        issues.append(HealthIssue(
            "warning",
            "Falta 'Use when/for ...' — el agente no sabe cuándo activarla",
            "Agregá al final: 'Use when [condición específica].'",
        ))

    # ── Good description bonus ───────────────────────────────────────
    if has_trigger and IDEAL_MIN_CHARS <= len(desc) <= IDEAL_MAX_CHARS and not found_broad:
        score = min(100, score + 10)

    return SkillHealth(
        skill=skill,
        score=max(0, min(100, score)),
        issues=issues,
    )


# ── Conflict detection ────────────────────────────────────────────────────────

def detect_conflicts(skills: list[Skill]) -> list[Conflict]:
    """Find pairs of skills with significantly overlapping trigger keywords."""
    conflicts: list[Conflict] = []

    keyword_sets = [
        (s, _meaningful_words(s.description) - BROAD_KEYWORDS)
        for s in skills
    ]

    for i, (s1, kw1) in enumerate(keyword_sets):
        for s2, kw2 in keyword_sets[i + 1:]:
            shared = kw1 & kw2
            if len(shared) >= CONFLICT_THRESHOLD:
                conflicts.append(Conflict(s1, s2, sorted(shared)))

    return conflicts


# ── Main entry point ──────────────────────────────────────────────────────────

def run_audit(skills: list[Skill]) -> AuditReport:
    health    = [score_skill(s) for s in skills]
    conflicts = detect_conflicts(skills)
    return AuditReport(skills=health, conflicts=conflicts)
