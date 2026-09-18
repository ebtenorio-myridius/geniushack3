# Presentation Pack

This folder contains the presentation outline, walkthrough script, and evidence matrix for the Genius Hacks submission.

## Files

- `deck.md` - slide-by-slide presentation content.
- `demo-script.md` - the live demonstration sequence and fallback plan.
- `evidence-matrix.md` - mapping from judging criteria to repository evidence and remaining gaps.
- `Risk_Assessment_Workbench_Genius_Hacks_2026.pptx` - editable presentation deck generated from the materials above.

Regenerate the deck after changing the outline or measured results:

```bash
python tools/generate_presentation.py
```

The presentation should describe the current implementation accurately. Policy
evidence lookup, a committee decision endpoint, demo role headers, telemetry,
and live LLM evaluation are implemented. Real identity, multi-member quorum,
and production residual-risk controls remain planned extensions.
