# Demo video kit

Cinematic intro, chapter cards, Level 1 / Level 2 motion graphics, end card, and an original synthesized score.
`tools/assemble.py` stitches everything with the screen recordings into `out/demo.mp4`, keeping the
3 minute and file-size limits from the participant guide (section 7.7).

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
