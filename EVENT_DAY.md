# Event day plan (Oct 10, 9 AM, NASTP Arena)

## Night before

- [ ] Both servers start with no errors (see README) and `uv run pytest -q` passes
- [ ] Two Gemini keys in `backend/.env` (one per Google account or project). One real test call each
- [ ] Optional: Groq or OpenRouter key in `FALLBACK_*`
- [ ] GitHub repo created and pushed, logged in on your laptop
- [ ] Laptop, charger, phone hotspot, ID and your confirmation email
- [ ] Read the follow-up guidelines email from the organizers (rules, what is allowed, how to submit)

## The 3 hours (individual, timed)

| Time | Do this |
|---|---|
| 0:00 - 0:15 | Read the challenge twice. Open the dataset. Run `uv run python scripts/profile_data.py <file>` and load it in the Workspace |
| 0:15 - 0:30 | Pick ONE clear user and ONE core feature. Write the problem in one sentence. Choose the mode that fits (analyze, docs, extract or classify, predict) |
| 0:30 - 1:45 | Make the core feature work end to end. Edit prompts in the module, or write `solve_challenge()` in `backend/app/custom.py`. Test with real data every 15 minutes |
| 1:45 - 2:15 | Fix the top 3 problems. Edit `frontend/lib/config.ts` (name, tagline, problem, steps) so the pages tell your story |
| 2:15 - 2:40 | README (fill the blanks), screenshots, push to GitHub. Deploy only if everything else is done |
| 2:40 - 3:00 | Practice the demo twice with `DEMO_SCRIPT.md`. Save a backup screenshot of a good result |

## Rules of thumb

- A small thing that works beats a big thing that breaks.
- Commit to GitHub every 30 minutes.
- If Gemini rate limits you: the backup key switches in automatically. If both fail, add a fallback provider or wait 60 seconds.
- Do not change the theme or fonts on the day. Change text only.
- Keep the same question you demo 100 percent tested.

## Where to edit what

| I want to change | File |
|---|---|
| Project name, tagline, problem, steps, team | `frontend/lib/config.ts` |
| Colors and fonts | `frontend/app/globals.css` (top block) |
| How the AI behaves for the challenge | `backend/app/custom.py` and `backend/app/modules/*.py` |
| Which model | `GEMINI_MODEL` in `backend/.env` |
