# Demo video kit

Cinematic intro, chapter cards, Level 1 / Level 2 motion graphics, end card, and an original synthesized score.
`tools/assemble.py` stitches everything with the screen recordings into `out/demo.mp4`, keeping the
3 minute and file-size limits from the participant guide (section 7.7).

## Shot list (what the judges must see, guide section 7.7)

Before recording: terminal full screen, font 18pt or larger, dark theme, close notifications, `.env` not on screen.

| Clip | Length | Show |
|---|---|---|
| `raw/01_launch.mp4` | 5-8 s | Type and run the start command. |
| `raw/02_extract.mp4` | 8-12 s | Bill image `KESC_0008` open next to the terminal, run Level 1, JSON prints. |
| `raw/03_ask.mp4` | 8-12 s | Ask 2-3 questions about the same bill, answers print. |
| `raw/04_batch.mp4` | any | Run on the 10 test bills until `level1.csv` and `level2.csv` are written; open one CSV at the end. Long runs: set `"speed": 4` in `timeline.json`. |

The decode and Q&A slides replay the real output in motion graphics, so they must be fed from the run you recorded.

## Make the final video

1. Record the terminal (Win + Shift + R) and save the clips into `raw/`:
   `01_launch.mp4`, `02_extract.mp4` (KESC_0008 bill visible), `03_ask.mp4`, `04_batch.mp4`.
2. Paste the CLI's real output into `slides/data/level1.json` (KESC_0008 JSON) and `slides/data/level2.json` (3 Q&As).
   The current values are the guide's sample answers, for preview only.
3. Check `slides/data/project.json` (name, model, stats).
4. Run it:
   ```
   python3 -m http.server 8765 &      # from video/
   python3 tools/assemble.py
   ```
   Trim long clips with `"from"`/`"to"` or speed them up with `"speed"` in `timeline.json`.
