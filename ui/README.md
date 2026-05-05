# A2 Render Workbench

Gradio frontend for the assignment renderer.

## Run

1. Install Gradio in your Python environment.
2. Start the app from the repo root:

```bash
python3 ui/app.py
```

3. Open the local URL printed by Gradio.

To force a specific port, set `GRADIO_SERVER_PORT`, for example:

```bash
GRADIO_SERVER_PORT=8080 python3 ui/app.py
```

## What It Does

- Builds the project with `cmake --build build`
- Runs `build/a2` with scene and image options from the page
- Supports the renderer's `-jitter` and `-filter` sampling flags from the UI
- Writes generated images to `ui/runs/`
- Shows generated outputs next to reference renders from `sample_solution/athena/a2`
- Logs the exact commands and their stdout/stderr
