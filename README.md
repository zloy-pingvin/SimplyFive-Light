# SimplyFive Light — One-click LOD Generator for Blender

A Blender add-on that generates a set of LOD meshes (Levels of Detail) from
the active object. For each mesh you can create up to 5 simplified versions,
each with its own triangle percentage and quality mode — in one click.

**Light** is the free version. It is fully self-contained and useful on its
own; a separate **Pro** version adds fine-grained per-LOD control and extra
transfer options (see *Pro version* below).

Author: zloy_pingvin
Requires Blender: 4.2.0+ (verified on 4.2, 4.5.11 LTS, 5.0 and 5.2 LTS)


## Features (Light)

- Up to 5 LOD levels per object, each with its own triangle percentage.
- 5 one-click quality modes per level: **Careful**, **Standard**,
  **Aggressive**, **Very Aggressive** and **Very Aggressive Alternative** —
  the farther the level, the more aggressive the mode. The two Very Aggressive
  modes differ in one thing: the Alternative finishes with a Decimate pass to
  reach the exact percentage, which suits some models and not others.
- **Recalculate + Smooth** on the Very Aggressive modes: rebuilds normals from
  the simplified geometry, since the source ones stop matching it at very low
  triangle counts.
- Attribute-aware simplification: keeps UVs and normals so seams and hard
  edges survive.
- Vertex colors carried onto the LODs, and optionally used as a per-vertex
  **importance map** — paint the areas you want to keep detailed, from either a
  color attribute or a vertex group. One global switch applied to every level.
- **Source checks** (Preferences) that catch the two things which silently stop
  simplification dead: a UV map that was never unwrapped, and a surface
  duplicated to carry a second material. Both are reported before generating,
  and both can be worked around automatically.
- **Optimize for GPU**: reorders triangles and vertices the way the GPU reads
  them, without changing the geometry.
- Multiple UV channels: carry every UV channel onto the LODs, not just the
  active one.
- Multi-material support, including materials on linked duplicates/instances
  or produced by Geometry Nodes.
- Merge by Distance on the result to weld seams cleanly.
- Configurable LOD name suffix (Preferences), default `_lod_`.
- In-viewport LOD preview slider, plus a **Line Up LODs** review mode that
  lays all levels out in a row for side-by-side comparison.
- Optional once-a-day update check against the product site, off with one
  switch — with it off the add-on never touches the network.
- Russian UI translation.

## Pro version

<https://zloy-pingvin.github.io/SimplyFive-Light/>

The Pro version keeps everything in Light and adds:

- Full per-level fine-tuning of every simplification parameter. Light shows the
  same block greyed out, so you can see what each level is generated with.
- Chained LODs — build each level from the previous one for cleaner far LODs.
- Vertex color **hard-lock**: guarantee important areas are never simplified.
- Per-level importance mask, so a near level can anchor a little of it and a
  distant one all of it.
- Recalculate normals + Auto Smooth by angle, and a Sharp Loops mode that
  closes broken feature loops, for very low-poly levels.
- **Accurate Vertex Colors**: blend colors along the collapse so a painted
  gradient does not come out in steps.
- **Protect Material Borders** as a switch of its own, separate from UV seams.
- **Limit Prune**: stop pruning from deleting whole parts.
- An extra topology-ignoring ultra-aggressive mode, a voxel remesh, and a
  "regularize" pass for more uniform triangles.
- Save and load full configurations as named presets, plus editable mode
  presets.

## Installation

1. Blender → Edit → Preferences → Add-ons.
2. Open the drop-down at the top right → "Install from Disk…" → select the
   SimplyFive Light archive.
3. Enable the checkbox next to "SimplyFive Light".

The simplification library is already bundled — no extra build step is
required.

## Quick Start

1. Select a mesh object in the viewport.
2. Open the sidebar (N) → "LODS" tab.
3. Set "Number of LODs" (3–4 is usually enough).
4. For each level, choose a mode (Careful / Standard / Aggressive / Very
   Aggressive) — the farther the level is from "0", the more aggressive the
   mode should be.
5. Optionally adjust the triangle percentage (%) for each level.
6. Click "Generate LODs".

The source object is renamed to "name_lod_0", and "name_lod_1",
"name_lod_2", etc. appear next to it — one per level (the `_lod_` suffix is
configurable in Preferences). The "LOD Preview (distance)" slider inspects
each level individually, and the icon button next to it ("Line Up LODs")
lays every generated level out in a row for side-by-side comparison.

Full documentation: <https://zloy-pingvin.github.io/SimplyFive-Light/docs.html>

## License

SimplyFive Light is licensed under the **GNU General Public License v3.0 or
later**. Full text — see the `LICENSE` file next to the add-on.

The add-on uses the **meshoptimizer** library (by Arseny Kapoulkine,
MIT License): https://github.com/zeux/meshoptimizer. The full meshoptimizer
license text and usage notice — see the `THIRD-PARTY-NOTICES.txt` file next
to the add-on.
