# Git + GitHub

## Purpose
Git workflow, conventional commits, PR templates, and branch protection best practices.

## Git Flow
```bash
# Feature
git checkout -b feat/user-auth
git add -p                        # stage hunks interactively
git commit -m "feat(auth): add JWT login endpoint"
git push origin feat/user-auth
# → open PR → review → squash merge → delete branch

# Hotfix
git checkout -b hotfix/fix-null-pointer main
git commit -m "fix: prevent null pointer in token parser"
git push && gh pr create --base main
```

## Conventional Commits
```
feat(scope): add new feature         → minor version bump
fix(scope): patch a bug              → patch version bump
docs: update README                  → no version bump
refactor: restructure auth module
test: add unit tests for parser
chore: upgrade dependencies
perf: optimize N+1 query
BREAKING CHANGE: rename API endpoint → major version bump
```

## PR Template (.github/pull_request_template.md)
```markdown
## Summary
Brief description of changes.

## Type
- [ ] feat  - [ ] fix  - [ ] refactor  - [ ] docs

## Testing
- [ ] Unit tests added/updated
- [ ] Manually tested locally

## Checklist
- [ ] No hardcoded secrets
- [ ] No debug logs left
- [ ] Migrations included (if DB changes)
```

## Branch Protection (via GitHub)
```
main:
  - Require PR review (1+ approvers)
  - Require status checks (CI must pass)
  - No force push
  - No direct commits
```

## Useful Aliases
```bash
git config --global alias.lg "log --oneline --graph --decorate --all"
git config --global alias.undo "reset HEAD~1 --soft"
git config --global alias.stash-all "stash save --include-untracked"
```

## Key Patterns
- Commit early, commit often — small atomic commits
- `git rebase -i HEAD~n` to squash before PR
- `git bisect` to find regressions
- Use `.gitattributes` to normalize line endings
- Tag releases: `git tag -a v1.0.0 -m "Release 1.0.0"`
