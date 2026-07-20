# SimplyFive Light — One-click LOD Generator for Blender

A Blender add-on that generates a set of LOD meshes (Levels of Detail) from
the active object. For each mesh you can create up to 5 simplified versions,
each with its own triangle percentage and quality mode — in one click.

**Light** is the free version. It is fully self-contained and useful on its
own; a separate **Pro** version adds fine-grained per-LOD control and extra
transfer options (see *Pro version* below).

Author: zloy_pingvin
Requires Blender: 5.2.0+


## Features (Light)

- Up to 5 LOD levels per object, each with its own triangle percentage.
- 4 one-click quality modes per level: **Careful**, **Standard**,
  **Aggressive**, **Very Aggressive** — the farther the level, the more
  aggressive the mode.
- Attribute-aware simplification: keeps UVs and normals so seams and hard
  edges survive.
- Vertex colors carried onto the LODs, and optionally used as a per-vertex
  **importance map** (paint areas you want to keep more detailed) — one
  global switch applied to every level.
- Multi-material support, including materials on linked duplicates/instances
  or produced by Geometry Nodes.
- Merge by Distance on the result to weld seams cleanly.
- Configurable LOD name suffix (Preferences), default `_lod_`.
- In-viewport LOD preview slider, plus a **Line Up LODs** review mode that
  lays all levels out in a row for side-by-side comparison.
- Russian UI localization.

## Pro version

The Pro version keeps everything in Light and adds:

- Full per-level fine-tuning of every simplification parameter.
- Chained LODs — build each level from the previous one for cleaner far LODs.
- Multiple UV channels transfer (not just the active one).
- Vertex color **hard-lock**: guarantee important areas are never simplified.
- Recalculate normals + Auto Smooth by angle for very low-poly levels.
- An extra topology-ignoring ultra-aggressive mode, and a "regularize" pass
  for more uniform triangles.
- Save and load full configurations as named presets.

*(availability and purchase link — coming soon.)*

## Installation

1. Blender → Edit → Preferences → Add-ons.
2. "Install..." → select the SimplyFive Light folder/archive.
3. Enable the checkbox next to "SimplyFive Light (lod generator)".

The simplification library is already bundled — no extra build step is
required.

## Quick Start

1. Select a mesh object in the viewport.
2. Open the sidebar (N) → "LODs" tab.
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

## License

SimplyFive Light is licensed under the **GNU General Public License v3.0 or
later**. Full text — see the `LICENSE` file next to the add-on.

The add-on uses the **meshoptimizer** library (by Arseny Kapoulkine,
MIT License): https://github.com/zeux/meshoptimizer. The full meshoptimizer
license text and usage notice — see the `THIRD-PARTY-NOTICES.txt` file next
to the add-on.
