# Development workflow

This is the starting version. Milestone M10 ([#10](https://github.com/Sportx666/sistematic_trading/issues/10)) expands it with issue templates, labels and optional automation.

1. **Issue.** Every piece of work starts as a GitHub issue with deliverables and acceptance criteria.
2. **Branch.** `claude/issue-<n>-<short-slug>` (or `<user>/issue-<n>-<slug>` for manual work).
3. **Implement in small steps.** Keep each PR focused and reviewable, preferably under ~400 changed lines. Split large milestones into several PRs.
4. **Local checks before pushing:**
   ```bash
   uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
   ```
5. **Pull request.** Reference the issue (`Part of #n` / `Closes #n`). Fill in the PR template's safety checklist.
6. **CI** must be green.
7. **Review** by the repository owner, with ChatGPT as a second reviewer. Address the comments in follow-up commits on the same branch.
8. **Manual merge** by the owner. Nothing is auto-merged or auto-deployed.
9. **Journal.** Record what was learned in `journal/` and update `progress/TRACKER.md`.

## What always needs explicit owner approval

- Any code that talks to a broker API
- Changing `LIVE_TRADING_ALLOWED`
- Moving from paper trading to real capital (see the go/no-go checklist in M8)
