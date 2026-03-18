"""
PISKU Recommender — maps a user profile to a ranked list of skill names.
Pure logic, no I/O.
"""

# Mapping: (dev_type, stack_item) → skill names
SKILL_MAP: dict[str, list[str]] = {
    # By dev type
    "junior_backend":   ["python-fastapi", "postgresql-sqlalchemy", "docker-ci-cd", "git-github", "testing-pytest"],
    "senior_fullstack": ["python-fastapi", "react-typescript", "postgresql-sqlalchemy", "docker-ci-cd", "testing-pytest"],
    "web3":             ["solidity-base", "python-fastapi", "git-github"],
    "devops":           ["docker-ci-cd", "git-github", "postgresql-sqlalchemy"],
    "data":             ["postgresql-sqlalchemy", "python-fastapi", "testing-pytest", "django-orm"],

    # By stack item
    "python":       ["python-fastapi", "testing-pytest"],
    "django":       ["django-orm"],
    "postgresql":   ["postgresql-sqlalchemy"],
    "supabase":     ["supabase"],
    "solidity":     ["solidity-base"],
    "docker":       ["docker-ci-cd"],
    "react":        ["react-typescript"],
    "typescript":   ["react-typescript"],
    "nodejs":       ["react-typescript", "git-github"],
    "redis":        ["docker-ci-cd"],
    "mongodb":      [],
    "go":           [],
}

REASON_MAP: dict[str, str] = {
    "junior_backend":   "Junior Backend → Python + PostgreSQL + Docker",
    "senior_fullstack": "Senior Fullstack → FastAPI + React + testing",
    "web3":             "Web3 Developer → Solidity + Python backend",
    "devops":           "DevOps → Docker CI/CD + Git workflow",
    "data":             "Data Engineer → PostgreSQL + Python + Django ORM",
}


def get_recommendations(profile: dict) -> dict:
    """
    Returns:
        {
          "skills": ["python-fastapi", ...],   # ordered, deduplicated
          "reason": "Junior Backend → ...",
          "indices": [],                        # filled by caller once menu is built
        }
    """
    dev_type = profile.get("dev_type", "")
    stack    = profile.get("stack", [])

    seen: dict[str, int] = {}   # skill → score (higher = more relevant)

    # Dev type gives base score
    for skill in SKILL_MAP.get(dev_type, []):
        seen[skill] = seen.get(skill, 0) + 2

    # Each stack item adds 1
    for item in stack:
        for skill in SKILL_MAP.get(item, []):
            seen[skill] = seen.get(skill, 0) + 1

    # Sort by score desc, keep insertion order for ties
    ranked = sorted(seen.keys(), key=lambda s: -seen[s])

    return {
        "skills": ranked,
        "reason": REASON_MAP.get(dev_type, "Perfil personalizado"),
        "indices": [],   # populated externally after menu indices are known
    }
