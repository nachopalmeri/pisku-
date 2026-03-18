"""
Tests for recommender logic and its integration with skills_puller.

Run:
    pytest tests/test_recommender_integration.py -v
"""
import sys
from pathlib import Path

# Add project root
root = Path(__file__).parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from cli.recommender import get_recommendations


# ══════════════════════════════════════════════════════════════════════════════
#  Core recommender logic
# ══════════════════════════════════════════════════════════════════════════════

class TestGetRecommendations:

    def test_junior_backend_gets_fastapi(self):
        profile = {"dev_type": "junior_backend", "stack": ["python"], "ai": "claude"}
        result = get_recommendations(profile)
        assert "python-fastapi" in result["skills"]

    def test_junior_backend_gets_postgresql(self):
        profile = {"dev_type": "junior_backend", "stack": ["postgresql"], "ai": "claude"}
        result = get_recommendations(profile)
        assert "postgresql-sqlalchemy" in result["skills"]

    def test_web3_dev_gets_solidity(self):
        profile = {"dev_type": "web3", "stack": ["solidity"], "ai": "claude"}
        result = get_recommendations(profile)
        assert "solidity-base" in result["skills"]

    def test_web3_does_not_get_django(self):
        profile = {"dev_type": "web3", "stack": ["solidity"], "ai": "claude"}
        result = get_recommendations(profile)
        assert "django-orm" not in result["skills"]

    def test_devops_gets_docker(self):
        profile = {"dev_type": "devops", "stack": ["docker"], "ai": "claude"}
        result = get_recommendations(profile)
        assert "docker-ci-cd" in result["skills"]

    def test_fullstack_gets_react(self):
        profile = {"dev_type": "senior_fullstack", "stack": ["react"], "ai": "claude"}
        result = get_recommendations(profile)
        assert "react-typescript" in result["skills"]

    def test_empty_stack_still_returns_skills(self):
        profile = {"dev_type": "junior_backend", "stack": [], "ai": "claude"}
        result = get_recommendations(profile)
        assert len(result["skills"]) > 0

    def test_unknown_dev_type_returns_something(self):
        profile = {"dev_type": "unknown_type", "stack": [], "ai": "claude"}
        result = get_recommendations(profile)
        assert isinstance(result["skills"], list)   # might be empty but no crash

    def test_result_has_reason(self):
        profile = {"dev_type": "junior_backend", "stack": ["python"], "ai": "claude"}
        result = get_recommendations(profile)
        assert "reason" in result
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0

    def test_no_duplicate_skills(self):
        profile = {
            "dev_type": "junior_backend",
            "stack": ["python", "postgresql", "docker"],
            "ai": "claude"
        }
        result = get_recommendations(profile)
        assert len(result["skills"]) == len(set(result["skills"]))

    def test_stack_skills_boost_ranking(self):
        """Skills matching both dev_type AND stack items should rank higher."""
        profile = {
            "dev_type": "junior_backend",
            "stack": ["python", "postgresql"],
            "ai": "claude"
        }
        result = get_recommendations(profile)
        skills = result["skills"]
        # python-fastapi matches dev_type + stack["python"] → should be near top
        assert skills.index("python-fastapi") < len(skills) // 2

    def test_supabase_stack_item(self):
        profile = {"dev_type": "junior_backend", "stack": ["supabase"], "ai": "claude"}
        result = get_recommendations(profile)
        assert "supabase" in result["skills"]

    def test_django_stack_item(self):
        profile = {"dev_type": "data", "stack": ["django"], "ai": "claude"}
        result = get_recommendations(profile)
        assert "django-orm" in result["skills"]


# ══════════════════════════════════════════════════════════════════════════════
#  Skills puller ★ marks (pure logic — no network)
# ══════════════════════════════════════════════════════════════════════════════

class TestSkillsPullerRecommendations:
    """
    Tests that the SkillsPuller correctly marks recommended skills
    without making any network calls.
    """

    def _load_puller(self):
        import types
        for mod_name in ["rich", "rich.console", "rich.table", "rich.panel",
                         "rich.prompt", "rich.syntax"]:
            if mod_name not in sys.modules:
                m = types.ModuleType(mod_name)
                m.Console = lambda: type("C", (), {"print": lambda *a, **k: None})()
                m.Table   = lambda **kw: None
                m.Panel   = lambda *a, **kw: None
                m.Confirm = type("Confirm", (), {"ask": staticmethod(lambda *a, **k: True)})
                m.Prompt  = type("Prompt",  (), {"ask": staticmethod(lambda *a, **k: "1")})
                m.Syntax  = lambda *a, **kw: None
                m.box     = type("box", (), {"ROUNDED": None})
                sys.modules[mod_name] = m
        if "httpx" not in sys.modules:
            mock_httpx = types.ModuleType("httpx")
            mock_httpx.ConnectError    = ConnectionError
            mock_httpx.HTTPStatusError = Exception
            sys.modules["httpx"] = mock_httpx
        import importlib
        if "cli.skills_puller" in sys.modules:
            del sys.modules["cli.skills_puller"]
        return importlib.import_module("cli.skills_puller")

    def test_recommended_set_stored(self):
        sp = self._load_puller()
        puller = sp.SkillsPuller(
            user_skills_dir=Path("/tmp"),
            recommended_skill_names=["python-fastapi", "solidity-base"],
        )
        assert "python-fastapi" in puller.recommended
        assert "solidity-base" in puller.recommended

    def test_empty_recommendations(self):
        sp = self._load_puller()
        puller = sp.SkillsPuller(user_skills_dir=Path("/tmp"))
        assert puller.recommended == set()

    def test_recommended_match_detection(self):
        sp = self._load_puller()
        puller = sp.SkillsPuller(
            user_skills_dir=Path("/tmp"),
            recommended_skill_names=["python-fastapi"],
        )
        skills = [
            sp.RemoteSkill("python-fastapi", "", "r/r", "s/SKILL.md", "main", ""),
            sp.RemoteSkill("solidity-base", "", "r/r", "s/SKILL.md", "main", ""),
        ]
        marked = [s for s in skills if s.name in puller.recommended]
        assert len(marked) == 1
        assert marked[0].name == "python-fastapi"
