from __future__ import annotations

import hashlib
import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import gradio as gr


ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "build"
BIN_PATH = BUILD_DIR / "a2"
REFERENCE_BIN_PATH = ROOT / "sample_solution" / "athena" / "a2"
DATA_DIR = ROOT / "data"
RUNS_DIR = ROOT / "ui" / "runs"
REFERENCE_DIR = ROOT / "ui" / "reference"

RUNS_DIR.mkdir(parents=True, exist_ok=True)
REFERENCE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class SceneConfig:
    key: str
    label: str
    scene_file: str
    sample_prefix: str
    default_depth_min: float
    default_depth_max: float
    default_bounces: int = 0
    default_shadows: bool = False


SCENES = [
    SceneConfig("plane", "Scene 01 Plane", "scene01_plane.txt", "a01", 8.0, 18.0),
    SceneConfig("cube", "Scene 02 Cube", "scene02_cube.txt", "a02", 8.0, 18.0),
    SceneConfig("sphere", "Scene 03 Sphere", "scene03_sphere.txt", "a03", 8.0, 18.0),
    SceneConfig("axes", "Scene 04 Axes", "scene04_axes.txt", "a04", 8.0, 18.0),
    SceneConfig("bunny_200", "Scene 05 Bunny 200", "scene05_bunny_200.txt", "a05", 0.8, 1.0),
    SceneConfig("bunny_1k", "Scene 06 Bunny 1K", "scene06_bunny_1k.txt", "a06", 8.0, 18.0, 4, False),
    SceneConfig("arch", "Scene 07 Arch", "scene07_arch.txt", "a07", 8.0, 18.0, 4, True),
]

SCENE_BY_KEY = {scene.key: scene for scene in SCENES}
SCENE_LABEL_TO_KEY = {scene.label: scene.key for scene in SCENES}


def scene_from_label(label: str) -> SceneConfig:
    return SCENE_BY_KEY[SCENE_LABEL_TO_KEY[label]]


def output_name_for(scene: SceneConfig) -> str:
    return f"{scene.sample_prefix}_custom"


def sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_size(path: Path) -> Optional[tuple[int, int]]:
    if not path.exists():
        return None

    with path.open("rb") as file:
        header = file.read(24)

    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None

    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    return width, height


def run_command(args: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    output = f"$ {' '.join(shlex.quote(arg) for arg in args)}\n"

    if completed.stdout:
        output += completed.stdout

    if completed.stderr:
        output += "\n[stderr]\n" + completed.stderr

    return completed.returncode, output


def comparison_text(generated: Path, sample: Path) -> str:
    if not generated.exists():
        return "Generated file missing"

    if not sample.exists():
        return "Reference file missing"

    generated_size = png_size(generated)
    sample_size = png_size(sample)
    generated_hash = sha256_for_file(generated)
    sample_hash = sha256_for_file(sample)

    match_text = "Exact byte match" if generated_hash == sample_hash else "Different bytes"

    return (
        f"{match_text}\n"
        f"generated size: {generated_size}\n"
        f"sample size: {sample_size}\n"
        f"generated sha256: {generated_hash[:16]}...\n"
        f"sample sha256:    {sample_hash[:16]}..."
    )


def generated_paths(stem: str) -> dict[str, Path]:
    return {
        "color": RUNS_DIR / f"{stem}.png",
        "normals": RUNS_DIR / f"{stem}_normals.png",
        "depth": RUNS_DIR / f"{stem}_depth.png",
    }


def reference_paths(stem: str) -> dict[str, Path]:
    return {
        "color": REFERENCE_DIR / f"{stem}.png",
        "normals": REFERENCE_DIR / f"{stem}_normals.png",
        "depth": REFERENCE_DIR / f"{stem}_depth.png",
    }


def image_value(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return str(path)


def render_args(
    scene: SceneConfig,
    stem: str,
    width: int,
    height: int,
    bounces: int,
    shadows: bool,
    jitter: bool,
    filter_enabled: bool,
    normals_enabled: bool,
    depth_enabled: bool,
    depth_min: float,
    depth_max: float,
) -> list[str]:
    paths = generated_paths(stem)

    args = [
        "-input",
        str(DATA_DIR / scene.scene_file),
        "-size",
        str(int(width)),
        str(int(height)),
        "-output",
        str(paths["color"]),
    ]

    if shadows:
        args.append("-shadows")

    if int(bounces):
        args.extend(["-bounces", str(int(bounces))])

    if jitter:
        args.append("-jitter")

    if filter_enabled:
        args.append("-filter")

    if normals_enabled:
        args.extend(["-normals", str(paths["normals"])])

    if depth_enabled:
        args.extend([
            "-depth",
            str(float(depth_min)),
            str(float(depth_max)),
            str(paths["depth"]),
        ])

    return args


def user_render_args(scene: SceneConfig, stem: str, *params) -> list[str]:
    return [str(BIN_PATH), *render_args(scene, stem, *params)]


def reference_render_args(scene: SceneConfig, stem: str, *params) -> list[str]:
    reference_stem = f"{stem}_reference"
    generated = generated_paths(stem)
    reference = reference_paths(reference_stem)

    args = [str(REFERENCE_BIN_PATH), *render_args(scene, stem, *params)]

    rewritten: list[str] = []
    for arg in args:
        if arg == str(generated["color"]):
            rewritten.append(str(reference["color"]))
        elif arg == str(generated["normals"]):
            rewritten.append(str(reference["normals"]))
        elif arg == str(generated["depth"]):
            rewritten.append(str(reference["depth"]))
        else:
            rewritten.append(arg)

    return rewritten


def preview_outputs(stem: str):
    generated = generated_paths(stem)
    reference = reference_paths(f"{stem}_reference")

    color_caption = comparison_text(generated["color"], reference["color"])
    normals_caption = comparison_text(generated["normals"], reference["normals"])
    depth_caption = comparison_text(generated["depth"], reference["depth"])

    paths_text = (
        f"Run: {stem}\n"
        f"Color:      {generated['color']}\n"
        f"Normals:    {generated['normals']}\n"
        f"Depth:      {generated['depth']}\n"
        f"RefColor:   {reference['color']}\n"
        f"RefNormals: {reference['normals']}\n"
        f"RefDepth:   {reference['depth']}"
    )

    return (
        image_value(generated["color"]),
        image_value(reference["color"]),
        color_caption,
        color_caption,
        image_value(generated["normals"]),
        image_value(reference["normals"]),
        normals_caption,
        normals_caption,
        image_value(generated["depth"]),
        image_value(reference["depth"]),
        depth_caption,
        depth_caption,
        paths_text,
    )


def append_command(args: list[str], log: str) -> tuple[bool, str]:
    code, output = run_command(args)
    log += output + "\n"

    if code != 0:
        log += f"\nCommand failed with exit code {code}\n"
        return False, log

    return True, log


def build_project(log: str):
    log += "Starting build...\n"
    ok, log = append_command(["cmake", "--build", str(BUILD_DIR)], log)
    status = "Build finished" if ok else "Build failed"
    return log, status


def render_scene(
    scene_label: str,
    width: int,
    height: int,
    bounces: int,
    shadows: bool,
    jitter: bool,
    filter_enabled: bool,
    normals_enabled: bool,
    depth_enabled: bool,
    depth_min: float,
    depth_max: float,
    output_stem: str,
    log: str,
):
    scene = scene_from_label(scene_label)
    stem = output_stem.strip() or output_name_for(scene)

    if not BIN_PATH.exists():
        return (*empty_preview(), log + "Binary missing. Build first.\n", "Binary missing", stem)

    if not REFERENCE_BIN_PATH.exists():
        return (*empty_preview(), log + "Reference binary missing.\n", "Reference binary missing", stem)

    params = (
        int(width),
        int(height),
        int(bounces),
        bool(shadows),
        bool(jitter),
        bool(filter_enabled),
        bool(normals_enabled),
        bool(depth_enabled),
        float(depth_min),
        float(depth_max),
    )

    log += f"Rendering {scene.label}...\n"

    ok, log = append_command(user_render_args(scene, stem, *params), log)
    if not ok:
        return (*preview_outputs(stem), log, "Render failed", stem)

    ok, log = append_command(reference_render_args(scene, stem, *params), log)
    if not ok:
        return (*preview_outputs(stem), log, "Reference render failed", stem)

    return (*preview_outputs(stem), log, "Render finished", stem)


def build_and_render(*args):
    *render_inputs, log = args
    log, build_status = build_project(log)

    if build_status != "Build finished":
        return (*empty_preview(), log, build_status, render_inputs[-1])

    return render_scene(*render_inputs, log)


def render_full_sample_suite(
    scene_label: str,
    jitter: bool,
    filter_enabled: bool,
    log: str,
):
    if not BIN_PATH.exists():
        return (*empty_preview(), log + "Binary missing. Build first.\n", "Binary missing")

    if not REFERENCE_BIN_PATH.exists():
        return (*empty_preview(), log + "Reference binary missing.\n", "Reference binary missing")

    selected_scene = scene_from_label(scene_label)

    for scene in SCENES:
        stem = scene.sample_prefix
        params = (
            800,
            800,
            scene.default_bounces,
            scene.default_shadows,
            bool(jitter),
            bool(filter_enabled),
            True,
            True,
            scene.default_depth_min,
            scene.default_depth_max,
        )

        log += f"Rendering suite item {scene.label}...\n"

        ok, log = append_command(user_render_args(scene, stem, *params), log)
        if not ok:
            return (*preview_outputs(stem), log, "Suite render failed")

        ok, log = append_command(reference_render_args(scene, stem, *params), log)
        if not ok:
            return (*preview_outputs(stem), log, "Reference suite render failed")

    return (*preview_outputs(output_name_for(selected_scene)), log, "Reference suite render finished")


def empty_preview():
    return (
        None, None, "", "",
        None, None, "", "",
        None, None, "", "",
        "",
    )


def on_scene_change(scene_label: str):
    scene = scene_from_label(scene_label)

    return (
        800,
        800,
        scene.default_bounces,
        scene.default_shadows,
        scene.default_depth_min,
        scene.default_depth_max,
        output_name_for(scene),
        *preview_outputs(output_name_for(scene)),
    )


first_scene = SCENES[0]

with gr.Blocks(title="A2 Render Workbench") as demo:
    gr.Markdown("# A2 Render Workbench")
    gr.Markdown("Build, render, inspect logs, and compare against sample outputs.")
    gr.Markdown("Sampling options pass `-jitter` and `-filter` to both user and reference renders.")

    status = gr.Textbox(label="Status", interactive=False)
    log = gr.Textbox(label="Log", lines=18, value="", interactive=False)

    with gr.Row():
        build_btn = gr.Button("Build")
        render_btn = gr.Button("Render")
        build_render_btn = gr.Button("Build + Render")
        suite_btn = gr.Button("Render Reference Suite")

    with gr.Row():
        with gr.Column(scale=1):
            scene_select = gr.Dropdown(
                choices=[scene.label for scene in SCENES],
                value=first_scene.label,
                label="Scene",
            )

            width = gr.Number(label="Width", value=800, precision=0)
            height = gr.Number(label="Height", value=800, precision=0)
            bounces = gr.Number(label="Bounces", value=first_scene.default_bounces, precision=0)

            shadows = gr.Checkbox(label="Enable shadows", value=first_scene.default_shadows)
            jitter = gr.Checkbox(label="Enable jitter sampling", value=False)
            filter_enabled = gr.Checkbox(label="Enable gaussian filter", value=False)
            normals_enabled = gr.Checkbox(label="Write normals image", value=True)
            depth_enabled = gr.Checkbox(label="Write depth image", value=True)

            depth_min = gr.Number(label="Depth min", value=first_scene.default_depth_min)
            depth_max = gr.Number(label="Depth max", value=first_scene.default_depth_max)

            output_stem = gr.Textbox(label="Output name", value=output_name_for(first_scene))

            latest_paths = gr.Textbox(label="Generated files", lines=8, interactive=False)

        with gr.Column(scale=2):
            with gr.Row():
                generated_color = gr.Image(label="Generated Color", type="filepath")
                reference_color = gr.Image(label="Reference Color", type="filepath")

            with gr.Row():
                generated_color_caption = gr.Textbox(label="Generated Color Comparison", lines=6)
                reference_color_caption = gr.Textbox(label="Reference Color Comparison", lines=6)

    with gr.Row():
        generated_normals = gr.Image(label="Generated Normals", type="filepath")
        reference_normals = gr.Image(label="Reference Normals", type="filepath")
        generated_depth = gr.Image(label="Generated Depth", type="filepath")
        reference_depth = gr.Image(label="Reference Depth", type="filepath")

    with gr.Row():
        generated_normals_caption = gr.Textbox(label="Generated Normals Comparison", lines=6)
        reference_normals_caption = gr.Textbox(label="Reference Normals Comparison", lines=6)
        generated_depth_caption = gr.Textbox(label="Generated Depth Comparison", lines=6)
        reference_depth_caption = gr.Textbox(label="Reference Depth Comparison", lines=6)

    preview_components = [
        generated_color,
        reference_color,
        generated_color_caption,
        reference_color_caption,
        generated_normals,
        reference_normals,
        generated_normals_caption,
        reference_normals_caption,
        generated_depth,
        reference_depth,
        generated_depth_caption,
        reference_depth_caption,
        latest_paths,
    ]

    render_inputs = [
        scene_select,
        width,
        height,
        bounces,
        shadows,
        jitter,
        filter_enabled,
        normals_enabled,
        depth_enabled,
        depth_min,
        depth_max,
        output_stem,
        log,
    ]

    render_outputs = [
        *preview_components,
        log,
        status,
        output_stem,
    ]

    build_btn.click(
        fn=build_project,
        inputs=[log],
        outputs=[log, status],
    )

    render_btn.click(
        fn=render_scene,
        inputs=render_inputs,
        outputs=render_outputs,
    )

    build_render_btn.click(
        fn=build_and_render,
        inputs=render_inputs,
        outputs=render_outputs,
    )

    suite_btn.click(
        fn=render_full_sample_suite,
        inputs=[scene_select, jitter, filter_enabled, log],
        outputs=[*preview_components, log, status],
    )

    scene_select.change(
        fn=on_scene_change,
        inputs=[scene_select],
        outputs=[
            width,
            height,
            bounces,
            shadows,
            depth_min,
            depth_max,
            output_stem,
            *preview_components,
        ],
    )


if __name__ == "__main__":
    server_port = 7860
    demo.launch(
        server_port=server_port,
        show_error=True,
    )
