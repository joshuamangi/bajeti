# Prompt-writing tools (not a stage)

Use these when a new backlog item or idea appears. Save the resulting prompt as a new stage file by copying an existing stage file and replacing its sections, then add it to the table in IMPLEMENTATION.md. The first prompt below already saves its output under `docs/stages/`.

```
I want to build/improve: <idea, in plain words>.
First read CLAUDE.md, docs/roadmap.md and docs/backlog.md, and the code areas this touches. Then write me a Claude Code prompt for it, saved as docs/stages/S<nn>-<slug>.md, with these sections:
- Task (one paragraph) and why it matters
- Context to read first (exact file paths)
- Constraints (security, user_id scoping, migrations, Pi resources, CSS conventions, public repo)
- Steps, in stages, with a "stop for review" after any design, migration or security change
- Edge cases to handle explicitly
- Tests required (including cross-user)
- Definition of done (verifiable)
- What NOT to do
- Open questions for me
Keep it under 60 lines. Ask me up to three questions first only if truly needed.
```

Prompt reviewer (run before using any prompt):

```
Review this prompt as a skeptical staff engineer: <paste prompt>. Find ambiguity, missing constraints, ways it could cause data loss or a security regression, and missing verification. Rewrite it tighter, and list what you changed.
```

Backlog grooming:

```
Read docs/backlog.md and docs/roadmap.md. Turn each backlog item into a GitHub-issue-ready epic with a checklist of small stories, an estimate (S/M/L), dependencies, and risks. Suggest an order that respects the agreed roadmap and the Pi's constraints. Output markdown only; do not create issues.
```

Weekly hygiene (a good `/weekly` slash command):

```
Run a weekly review: list open PRs and issues, check that docs match the code, scan the last week's diffs for secrets or IPs, check pip-audit/Dependabot output, confirm backups exist for each of the last 7 days (read-only commands I can run, give them to me), and list the 3 highest-value next tasks.
```
