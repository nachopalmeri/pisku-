"""
PISKU Session Predictor — simula qué skills van a disparar para una tarea.

El matching real que hace el agente es semántico (LLM-based), pero podemos
aproximarlo bien con keyword overlap entre la descripción y la tarea.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from cli.skill_scanner import Skill
from cli.skill_auditor  import _meaningful_words
from cli.skill_auditor  import BROAD_KEYWORDS, TRIGGER_PATTERNS, STOPWORDS


# ── Predicción result ─────────────────────────────────────────────────────────

@dataclass
class SkillPrediction:
    skill:      Skill
    confidence: str        # "high" | "medium" | "low"
    reason:     str        # human-readable explanation
    matched_on: list[str]  # keywords that triggered the match


@dataclass
class SessionPrediction:
    task:        str
    will_fire:   list[SkillPrediction]   # high confidence
    might_fire:  list[SkillPrediction]   # medium — needs attention
    wont_fire:   list[SkillPrediction]   # low / none

    @property
    def metadata_tokens(self) -> int:
        all_skills = [p.skill for p in self.will_fire + self.might_fire + self.wont_fire]
        return sum(s.metadata_tokens for s in all_skills)

    @property
    def fire_tokens(self) -> int:
        return sum(p.skill.body_tokens for p in self.will_fire)

    @property
    def noise_tokens(self) -> int:
        return sum(p.skill.body_tokens for p in self.might_fire)

    @property
    def total_estimated_tokens(self) -> int:
        return self.metadata_tokens + self.fire_tokens + self.noise_tokens

    @property
    def savings_if_fixed(self) -> int:
        """Tokens saved per session if might_fire skills get better descriptions."""
        return self.noise_tokens

    def clipboard_text(self) -> str:
        """Ready-to-paste text for the user to start their session."""
        lines = []

        if self.will_fire:
            skill_cmds = " ".join(f"/{p.skill.slug}" for p in self.will_fire)
            lines.append(f"Activá estas skills: {skill_cmds}")

        if self.might_fire:
            noise_list = ", ".join(p.skill.slug for p in self.might_fire)
            lines.append(
                f"Si se activan estas, ignoralas (no son relevantes): {noise_list}"
            )

        lines.append(
            f"\nContexto: {self.task}"
        )

        return "\n".join(lines)


# ── Core matching logic ───────────────────────────────────────────────────────

def _task_keywords(task: str) -> set[str]:
    """Extract meaningful keywords from the task description."""
    return _meaningful_words(task)


def _match_score(task_kw: set[str], skill: Skill) -> tuple[int, list[str]]:
    """
    Returns (score, matched_keywords).
    score: 0 = no match, 1 = weak, 2 = medium, 3+ = strong
    """
    desc_kw  = _meaningful_words(skill.description) - BROAD_KEYWORDS
    matched  = sorted(task_kw & desc_kw)
    score    = len(matched)

    # Bonus: description has trigger pattern AND task mentions something specific
    desc_l   = skill.description.lower()
    if any(p in desc_l for p in TRIGGER_PATTERNS) and score > 0:
        score += 1

    return score, matched


def predict(task: str, skills: list[Skill]) -> SessionPrediction:
    task_kw = _task_keywords(task)

    will_fire:  list[SkillPrediction] = []
    might_fire: list[SkillPrediction] = []
    wont_fire:  list[SkillPrediction] = []

    for skill in skills:
        score, matched = _match_score(task_kw, skill)
        desc_l         = skill.description.lower()
        is_broad       = bool(_meaningful_words(skill.description) & BROAD_KEYWORDS)

        if score >= 3:
            will_fire.append(SkillPrediction(
                skill=skill,
                confidence="high",
                reason=f"Matchea {len(matched)} keywords: {', '.join(matched[:4])}",
                matched_on=matched,
            ))

        elif score == 2 or (score >= 1 and is_broad):
            reason = (
                f"Matchea {len(matched)} keyword(s)"
                + (f": {', '.join(matched)}" if matched else "")
                + (" + descripción broad (over-match potencial)" if is_broad else "")
            )
            might_fire.append(SkillPrediction(
                skill=skill,
                confidence="medium",
                reason=reason,
                matched_on=matched,
            ))

        elif score == 1 and not is_broad:
            # 1 keyword match solo, sin broad — match muy débil
            might_fire.append(SkillPrediction(
                skill=skill,
                confidence="medium",
                reason=f"Match débil en: {', '.join(matched)}",
                matched_on=matched,
            ))

        else:
            wont_fire.append(SkillPrediction(
                skill=skill,
                confidence="low",
                reason="Sin keywords en común con la tarea",
                matched_on=[],
            ))

    # Sort: high-confidence first within each bucket
    will_fire.sort(key=lambda p: -len(p.matched_on))
    might_fire.sort(key=lambda p: -len(p.matched_on))

    return SessionPrediction(
        task=task,
        will_fire=will_fire,
        might_fire=might_fire,
        wont_fire=wont_fire,
    )
