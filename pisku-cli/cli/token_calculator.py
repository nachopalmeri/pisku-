"""
Token Calculator — Estimates token count and savings from skill selection.
Uses a simple characters/4 approximation (good enough for GPT-4/Claude).
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli.skills_manager import Skill

# Rough avg tokens if you sent ALL skills vs selected ones
CHARS_PER_TOKEN = 4


class TokenCalculator:
    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // CHARS_PER_TOKEN)

    def estimate_savings(self, selected_skills: list["Skill"]) -> int:
        """
        Estimate tokens saved by ONLY including selected skills
        vs sending everything. Returns the delta.
        """
        # Tokens in selected skills
        selected_tokens = sum(
            self.estimate_tokens(s.read()) for s in selected_skills
        )

        # Assume average unused skill is ~800 tokens and user has ~10 total
        # This gives a realistic savings estimate without access to all skills
        estimated_total_if_all_sent = selected_tokens + (800 * 5)
        saved = estimated_total_if_all_sent - selected_tokens
        return max(0, saved)

    def tokens_in_skills(self, skills: list["Skill"]) -> dict[str, int]:
        """Returns per-skill token count dict."""
        return {s.name: self.estimate_tokens(s.read()) for s in skills}
