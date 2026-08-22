# A Blender add-on that generates a set of LOD meshes (Level of Detail) from the active object, using the meshoptimizer library ( by Arseny Kapoulkine, distributed under the MIT License)   
# For each mesh you can create up to 5 simplified versions with individual aggressiveness settings;
# simplification can take UV unwrapping, normals, vertex colors (as an importance map), and materials into account.
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 zloy_pingvin

# Single source of truth for the version, kept at module level. Blender 4.2+
# treats blender_manifest.toml as authoritative and DELETES bl_info from the
# module when the add-on is installed as an extension - so any runtime read of
# bl_info['version'] (e.g. in the Preferences draw()) raises NameError on every
# redraw. Read VERSION instead; never bl_info at runtime.
VERSION = (1, 3, 9)

bl_info = {
    "name": "SimplyFive Light (lod generator)",
    "author": "zloy_pingvin",
    "version": VERSION,
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar (N-panel) > LODS",
    "description": (
        "Generate LOD meshes using meshoptimizer "
    ),
    "doc_url": "https://zloy-pingvin.github.io/SimplyFive-Light/docs.html",
    "category": "Mesh",
}

import bpy
from mathutils import Matrix, Vector
from . import translations
from . import native_build
from . import mesh_ops
from . import update_check
from .mesh_ops import (
    MESHOPT_LOCK_BORDER, MESHOPT_ERROR_ABSOLUTE, MESHOPT_PRUNE,
    SMOOTH_CREASE_ANGLE, simplify_object,
)
from .native_build import native_available, try_load_native
import math
import re
import time

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except Exception:
    np = None
    NUMPY_AVAILABLE = False


MAX_LODS = 5

# Light build flag. This is NOT a feature gate (there is no Pro code in this
# package to unlock) - it only toggles whether the panel shows the greyed
# "available in Pro" teaser rows. Flipping it changes labels, never behavior.
#   True  -> self-hosted / GitHub build: show the Pro teaser + upsell.
#   False -> Extensions Platform ("store") build: clean UI, no Pro mentions.
SHOW_PRO_TEASER = True

# Product site, manual and community channel. Opened with wm.url_open, which
# hands the URL to the browser - the add-on itself makes no request for these.
URL_MANUAL = "https://zloy-pingvin.github.io/SimplyFive-Light/docs.html"
URL_WEBSITE = "https://zloy-pingvin.github.io/SimplyFive-Light/index.html"
URL_TELEGRAM = "https://t.me/zloytux"

DEFAULT_LOD_SUFFIX = "_lod_"

_lod_re_cache = {}


def addon_prefs():
    """The AddonPreferences block, or None while it is unreachable: early
    registration, an add-on registered without an addons[] entry, and a mocked
    bpy in the tests. Callers must handle None - a missing preferences block
    must never raise mid-generation."""
    try:
        return bpy.context.preferences.addons[__name__].preferences
    except Exception:
        return None


def get_pref(name, default):
    """One AddonPreferences value, falling back to the documented default when
    the block is unreachable (see addon_prefs)."""
    prefs = addon_prefs()
    return default if prefs is None else getattr(prefs, name, default)


def get_lod_suffix():
    """The user-configured text between the base object name and the LOD
    index (AddonPreferences). Falls back to the default during early
    registration or if the user empties the field."""
    suffix = get_pref('lod_suffix', DEFAULT_LOD_SUFFIX)
    return suffix if suffix else DEFAULT_LOD_SUFFIX


def suspend_edit_mode(context):
    """Drop to Object Mode for the duration of a generation and report which
    object was being edited. Mandatory, not cosmetic: regeneration removes the
    old object, and removing one that is still in Edit Mode leaks its edit
    mesh. Returns the object's name, or None."""
    obj = context.object
    if obj is None or obj.mode != 'EDIT':
        return None
    name = obj.name
    bpy.ops.object.mode_set(mode='OBJECT')
    return name


def resume_edit_mode(context, name):
    """Re-enter Edit Mode on that object once it has been rebuilt, if the
    preference asks for it. The object is looked up by name because
    regeneration replaced it with a new datablock."""
    if not name:
        return
    try:
        if not bpy.context.preferences.addons[__name__].preferences.restore_edit_mode:
            return
    except Exception:
        return
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != 'MESH' or obj.name not in context.view_layer.objects:
        return
    if obj.hide_get() or not obj.visible_get():
        return
    for other in context.view_layer.objects:
        other.select_set(other is obj)
    context.view_layer.objects.active = obj
    try:
        bpy.ops.object.mode_set(mode='EDIT')
    except RuntimeError as exc:
        print(f"[LOD Generator] Could not return to Edit Mode on {name}: {exc}")


def lod_name(base, index):
    return f"{base}{get_lod_suffix()}{index}"


def match_lod_name(name):
    """re.Match with group(1) = base, group(2) = index, or None. Compiled
    per suffix and cached, so a suffix change in Preferences applies
    immediately."""
    suffix = get_lod_suffix()
    regex = _lod_re_cache.get(suffix)
    if regex is None:
        regex = re.compile(rf'^(.*){re.escape(suffix)}(\d+)$')
        _lod_re_cache[suffix] = regex
    return regex.match(name)


def resolve_lod0(obj):
    """Return (base_name, lod0_object). Renames obj to '<name><suffix>0' the
    first time any LOD is generated for it, per the naming convention the
    whole LOD family (index 0 = original, 1..N = generated) relies on."""
    m = match_lod_name(obj.name)
    if m:
        base = m.group(1)
        if m.group(2) == '0':
            return base, obj
        lod0 = bpy.data.objects.get(lod_name(base, 0))
        return base, (lod0 if lod0 is not None else obj)
    base = obj.name
    obj.name = lod_name(base, 0)
    if obj.data:
        obj.data.name = obj.name
    # Blender counts a rename as a geometry update. Without flushing it here it
    # arrives after the scan below is cached and kills the entry at once - the
    # first generation on an object without the suffix never cached anything.
    try:
        bpy.context.view_layer.update()
    except Exception:
        pass
    return base, obj


# Panel draw() runs on every UI redraw (each mouse move / slider tick), so
# the triangle count must not loop over polygons in Python there - on
# multi-million-poly meshes that froze the whole UI while editing LOD
# settings. Counted in C via foreach_get and cached until the mesh's
# polygon/vertex counts change.
_tri_count_cache = {}


def mesh_tri_count(me):
    validity = (len(me.polygons), len(me.vertices))
    cached = _tri_count_cache.get(me.name)
    if cached is not None and cached[0] == validity:
        return cached[1]
    if NUMPY_AVAILABLE:
        loop_totals = np.empty(validity[0], dtype=np.int32)
        me.polygons.foreach_get("loop_total", loop_totals)
        tri_count = int(np.maximum(loop_totals - 2, 0).sum())
    else:
        tri_count = sum(len(p.vertices) - 2 for p in me.polygons)
    _tri_count_cache[me.name] = (validity, tri_count)
    return tri_count


def find_lod_family(base):
    """{lod_index: object} for every existing '<base><suffix>N' object."""
    family = {}
    if not base:
        return family
    for o in bpy.data.objects:
        m = match_lod_name(o.name)
        if m and m.group(1) == base:
            family[int(m.group(2))] = o
    return family



FACTORY_MODE_PRESETS = {
    'CAREFUL': dict(lock_border=True,
                     use_prune=False, use_permissive=False, protect_uv_seams=False, protect_material_borders=False,
                     use_attributes=True, use_vertex_update=False,
                     normal_weight=0.5, uv_weight=0.5, target_error=0.02,
                     preprune_threshold=0.0, use_decimate_finish=False),
    'STANDARD': dict(lock_border=True,
                      use_prune=False, use_permissive=False, protect_uv_seams=False, protect_material_borders=False,
                      use_attributes=True, use_vertex_update=True,
                      normal_weight=0.5, uv_weight=0.5, target_error=0.15,
                     preprune_threshold=0.0, use_decimate_finish=False),
    'AGGRESSIVE': dict(lock_border=False,
                        use_prune=True, use_permissive=True, protect_uv_seams=True, protect_material_borders=False,
                        use_attributes=True, use_vertex_update=True,
                        normal_weight=0.2, uv_weight=0.2, target_error=0.3,
                     preprune_threshold=0.02, use_decimate_finish=False),
    # Pure meshopt: no Decimate finish, so the result keeps meshopt's topology
    # and may stop above the requested percentage when seams block it.
    'VERY_AGGRESSIVE': dict(lock_border=False,
                             use_prune=True, use_permissive=True, protect_uv_seams=False, protect_material_borders=False,
                             use_attributes=True, use_vertex_update=True,
                             normal_weight=0.01, uv_weight=1.0, target_error=0.5,
                     preprune_threshold=0.07, use_decimate_finish=False),
    # Same settings, finished with Decimate so the exact target is reached even
    # when meshopt stalls; that pass needs protected UV seams, so both are on
    # together. Which of the two wins depends on the model. (Light's only way to
    # turn the Decimate finish off, since per-LOD fields aren't editable here.)
    'VERY_AGGRESSIVE_ALT': dict(lock_border=False,
                             use_prune=True, use_permissive=True, protect_uv_seams=True, protect_material_borders=False,
                             use_attributes=True, use_vertex_update=True,
                             normal_weight=0.01, uv_weight=1.0, target_error=0.5,
                     preprune_threshold=0.07, use_decimate_finish=True),
}

# The fields a Mode preset writes onto a LOD slot when selected. These drive
# the actual meshoptimizer call. The Light UI does not expose them for manual
# per-LOD editing (that fine-tuning is a Pro feature), so a slot's effective
# values always come straight from its selected Mode. Sparse is NOT here - it
# is derived from the buffers at generation time (mesh_ops.apply_sparse_option).
# protect_uv_seams stays before use_decimate_finish: the finish pass relies on
# seam protection, so the mode sets the guard first.
PRESET_FIELDS = [
    "lock_border", "use_prune", "use_permissive", "protect_uv_seams",
    "protect_material_borders",
    "use_decimate_finish", "use_attributes", "use_vertex_update",
    "normal_weight", "uv_weight", "target_error", "preprune_threshold",
]


def get_mode_preset(mode):
    """Effective preset values for a mode - the add-on's built-in factory
    defaults (Light has no user-editable presets)."""
    return FACTORY_MODE_PRESETS.get(mode)


def _on_mode_change(self, context):
    """Selecting a Mode writes its factory values onto this slot; those are
    what the generator reads. This is the only way slot engine values change
    in Light (there is no manual per-LOD editing)."""
    preset = get_mode_preset(self.simplify_mode)
    if preset is None:
        return
    for key, value in preset.items():
        setattr(self, key, value)


class LodGenAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    check_updates: bpy.props.BoolProperty(
        name="Check Updates", default=True,
        description="Once a day, ask the product site whether a newer version "
                    "exists. One small request on a background thread, nothing "
                    "is downloaded or installed and no data about you is sent. "
                    "Works the same offline")

    # Written by the update check, read by draw(). Kept in Preferences so the
    # answer survives a restart and the request is not repeated every redraw.
    latest_version: bpy.props.StringProperty(default="")
    latest_url: bpy.props.StringProperty(default="")
    last_update_check: bpy.props.StringProperty(default="")

    restore_edit_mode: bpy.props.BoolProperty(
        name="Return to Edit Mode", default=True,
        description="Generating leaves Edit Mode, since regeneration replaces "
                    "the object. With this on, Edit Mode is re-entered on it "
                    "afterwards")

    lod_suffix: bpy.props.StringProperty(
        name="LOD Name Suffix", default=DEFAULT_LOD_SUFFIX,
        description="Text between the base object name and the LOD index "
                    "(e.g. '_lod_' gives 'Cube_lod_1'). Changing it does not "
                    "rename existing LODs - objects named with the old suffix "
                    "are no longer recognized as part of a LOD family")

    # Source checks live here rather than in the panel, as in Pro: they are a
    # once-set workflow preference, not something to decide per scene.
    check_unwrapped_uv: bpy.props.BoolProperty(
        name="Check UV Maps", default=True,
        description="Look for UV maps that were never unwrapped before "
                    "generating. Such a map gives most vertices 3 or more UVs, "
                    "which meshoptimizer treats as unmovable - simplification "
                    "then does nothing at all. One pass over the mesh per "
                    "source, cached until the geometry changes")
    skip_unwrapped_uv: bpy.props.BoolProperty(
        name="Ignore Unwrapped UV Maps", default=True,
        description="Leave such a map out of simplification. The LOD still gets "
                    "the map - Blender's own fill reproduces it exactly, since "
                    "there was nothing in it to carry")
    check_duplicate_faces: bpy.props.BoolProperty(
        name="Check Duplicate Surfaces", default=True,
        description="Look for faces lying exactly on top of other faces (a "
                    "surface duplicated for a second material). Both copies "
                    "become unmovable and take their neighbours with them. One "
                    "pass over the mesh per source, cached")
    remove_duplicate_faces: bpy.props.BoolProperty(
        name="Drop Duplicate Surfaces", default=True,
        description="Keep one copy of each duplicated face when simplifying. "
                    "The dropped copy takes its material with it, so a material "
                    "used only by that copy disappears from the LOD - the panel "
                    "says which")

    def draw(self, context):
        layout = self.layout

        # Same head as Pro: the switch that governs the check first, then the
        # version with its answer, then the links.
        head = layout.row(align=True)
        head.prop(self, "check_updates")
        head.operator("lodgenlight.check_updates", text="", icon='FILE_REFRESH')

        row = layout.row()
        row.label(text=f"SimplyFive Light {'.'.join(str(x) for x in VERSION)}")
        if update_available(self):
            alert = row.row()
            alert.alert = True
            alert.label(text=f"{self.latest_version} available!")
            alert.operator("wm.url_open", text="Download",
                           icon='IMPORT').url = self.latest_url or URL_WEBSITE
        elif self.latest_version:
            row.label(text="up to date", icon='CHECKMARK')
        elif self.last_update_check:
            row.label(text="no version published yet", icon='INFO')

        links = layout.row(align=True)
        links.scale_y = 1.2
        links.operator("wm.url_open", text="User Manual",
                       icon='HELP').url = URL_MANUAL
        links.operator("wm.url_open", text="Website",
                       icon='URL').url = URL_WEBSITE
        links.operator("wm.url_open", text="Telegram",
                       icon='COMMUNITY').url = URL_TELEGRAM

        layout.separator()
        box = layout.box()
        if native_available():
            box.label(text="Simplification library: ready", icon='CHECKMARK')
        else:
            box.label(text="Simplification library not found", icon='ERROR')
            box.label(text="Reinstall the add-on to restore the bundled library.",
                      icon='INFO')

        layout.separator()
        box = layout.box()
        box.label(text="Naming", icon='SORTALPHA')
        box.prop(self, "lod_suffix")
        box.label(text="Generated objects are named <object><suffix><N>. "
                       "The original becomes <object><suffix>0 on the "
                       "first Generate.", icon='INFO')

        layout.separator()
        box = layout.box()
        box.label(text="Source Checks", icon='VIEWZOOM')
        # Each action sits under the scan it needs, and greys out with it.
        box.prop(self, "check_duplicate_faces")
        sub = box.row()
        sub.enabled = self.check_duplicate_faces
        sub.separator(factor=2.0)
        sub.prop(self, "remove_duplicate_faces")
        box.prop(self, "check_unwrapped_uv")
        sub = box.row()
        sub.enabled = self.check_unwrapped_uv
        sub.separator(factor=2.0)
        sub.prop(self, "skip_unwrapped_uv")
        box.separator()
        box.prop(self, "restore_edit_mode")

        layout.separator()
        layout.label(text="Credits", icon='INFO')
        layout.label(text="Uses meshoptimizer by Arseny Kapoulkine (MIT License).")
        layout.label(text="https://github.com/zeux/meshoptimizer")


MODE_ITEMS = [
    ('CAREFUL', "Careful",
     "Most precise: locks open edges, low Target Error, no attribute-crossing"),
    ('STANDARD', "Standard",
     "Balanced: keeps UVs/normals, Vertex Update on, moderate Target Error"),
    ('AGGRESSIVE', "Aggressive",
     "Permissive + Prune + protected UV seams, higher Target Error"),
    ('VERY_AGGRESSIVE', "Very Aggressive",
     "Like Aggressive with very low attribute weights and a higher Target "
     "Error. meshopt only - may stop above the requested percentage"),
    ('VERY_AGGRESSIVE_ALT', "Very Aggressive Alternative",
     "Very Aggressive plus a Decimate pass down to the exact percentage, with "
     "UV seams protected. Which of the two works better depends on the model"),
]

# Modes that offer the Recalculate + Smooth checkbox. Only the very aggressive
# ones: that is where the source normals stop matching the geometry. On a gentle
# LOD recalculating them would throw away shading that is still correct.
SMOOTH_NORMALS_MODES = {'VERY_AGGRESSIVE', 'VERY_AGGRESSIVE_ALT'}

# ---------------------------------------------------------------------------
# Pro-only per-LOD fields: declaration only, never read
# ---------------------------------------------------------------------------
#
# The Details block mirrors Pro's per-LOD panel with every row greyed out, so
# what the paid version adds is visible instead of described in a bullet list.
# A greyed widget still needs a property to draw from, and the fields below
# exist for no other reason: nothing in this add-on or in mesh_ops reads them,
# and generation cannot see them.
#
# Three rules keep them inert, and verify_all enforces all three:
#   1. never in PRESET_FIELDS or FACTORY_MODE_PRESETS - a Mode switch must not
#      write them, and _on_mode_change must not carry them,
#   2. never accessed as slot.<name> anywhere - the draw code reaches them by
#      name through the table below, so a real read stands out,
#   3. names absent from mesh_ops.py entirely.
# Values stay at Pro's own factory values for these five Modes, which happen to
# be the neutral ones (Normals = Preserve, Regularize = Off, Sloppy and Voxel
# Remesh off) - so nothing shown here is a lie about the free version.
#
# The set is small because the mirror hides what Pro hides: a row Pro reveals
# only under a switch that is off in all five Modes can never appear, so
# declaring a property for it would be dead weight. That rules out the whole
# Normals sub-block (Preserve reveals nothing), Sloppy and Voxel Remesh (Pro
# offers those on Custom / Clear Simplify, Modes Light does not have) and Lock
# Threshold (revealed by Hard-Lock, which cannot be switched on here).
PRO_ONLY_SLOT_FIELDS = (
    "use_previous_lod", "limit_prune", "normals_mode", "regularize_mode",
    "blend_colors_meshopt",
)
# Same rules, but on the global props: Light's importance mask is one setting
# for all LODs, so Hard-Lock is drawn there instead of per LOD.
PRO_ONLY_GLOBAL_FIELDS = ("use_vcolor_lock",)
PRO_ONLY_FIELDS = PRO_ONLY_SLOT_FIELDS + PRO_ONLY_GLOBAL_FIELDS


def pro_only_annotations():
    """Names, ranges and tooltips copied verbatim from Pro, so hovering a
    greyed row explains the parameter instead of advertising at the user."""
    return {
        'use_previous_lod': bpy.props.BoolProperty(
            name="Build from Previous LOD", default=False,
            description="Simplify from the previous LOD instead of lod 0 "
                        "(chained LODs): gentler steps, accumulating error. The "
                        "percentage still means % of lod 0. Falls back to lod 0 "
                        "if the previous LOD is missing"),
        'limit_prune': bpy.props.BoolProperty(
            name="Limit Prune", default=False,
            description="Stop the prunes from deleting whole parts. Pre-prune "
                        "is capped at a small share of the triangles, and if "
                        "Prune still drops the result far below the requested "
                        "percentage, Target Error is lowered and simplification "
                        "re-run. Turn off when Prune is meant to strip parts "
                        "on a distant LOD"),
        # The modes are spelled out here because a greyed dropdown cannot be
        # opened - the per-item descriptions below are unreachable.
        'normals_mode': bpy.props.EnumProperty(
            name="Normals",
            description="Normals of the finished LOD. Source normals stop "
                        "matching the geometry at low polycounts.\n"
                        "Preserve: carry the source normals over.\n"
                        "Recalculate + Smooth: meshoptimizer generates them, "
                        "then relaxes them, keeping edges above the angle "
                        "hard.\n"
                        "Recalculate + Auto Smooth: recompute from the LOD's "
                        "own geometry, sharp above the angle.\n"
                        "Recalculate + Sharp Loops: the same, but broken "
                        "feature loops are closed",
            items=[
                ('PRESERVE', "Preserve (from source)",
                 "Carry the source mesh's normals onto the LOD. "
                 "Best while simplification is moderate"),
                ('RECALC_SMOOTH', "Recalculate + Smooth (experimental)",
                 "meshoptimizer generates the normals and then relaxes them, "
                 "keeping edges above the angle hard. Evens out the blotchy "
                 "shading an irregular triangulation leaves. Writes custom "
                 "split normals, so it replaces edge marking instead of "
                 "adding to it"),
                ('RECALC', "Recalculate + Auto Smooth",
                 "Discard source normals and recompute from the LOD's own "
                 "geometry, marking edges sharp above the angle threshold "
                 "(Shade Smooth by Angle). Predictable at very low polycounts"),
                ('RECALC_LOOPS', "Recalculate + Sharp Loops",
                 "Like Auto Smooth, but closes broken feature loops: a second, "
                 "lower angle continues a line that has already started, short "
                 "gaps are bridged, and stray fragments are dropped. For "
                 "decimated meshes where a single threshold leaves loops open"),
            ], default='PRESERVE'),
        'regularize_mode': bpy.props.EnumProperty(
            name="Regularize",
            description="meshopt_SimplifyRegularize: more uniform triangles, at "
                        "some cost to appearance and triangle count.\n"
                        "Off: no regularization.\n"
                        "Regularize Light: milder uniformity bias.\n"
                        "Regularize: full uniformity bias",
            items=[
                ('OFF', "Off", "No regularization"),
                ('LIGHT', "Regularize Light",
                 "meshopt_SimplifyRegularizeLight: milder uniformity bias"),
                ('FULL', "Regularize",
                 "meshopt_SimplifyRegularize: full uniformity bias"),
            ], default='OFF'),
        'blend_colors_meshopt': bpy.props.FloatProperty(
            name="Accurate Vertex Colors", default=0.0, min=0.0, max=1.0,
            precision=3,
            description="Blend vertex colors along the collapse instead of "
                        "keeping the surviving vertex's color. 0 is off. "
                        "Higher values also let the color steer which edges "
                        "collapse. Switches Vertex Update and Regularize on"),
    }


def make_lod_slot_class(class_name, default_percent, default_mode):
    """Each LOD slot gets its own PropertyGroup subclass so it can start with
    a different default percentage/Mode than the others. The engine fields
    below are written by the selected Mode (see _on_mode_change) and read by
    the generator; the panel draws them greyed in the Details mirror, so they
    can be seen but not edited (that fine-tuning is a Pro feature)."""
    preset = FACTORY_MODE_PRESETS[default_mode]
    annotations = {
        'percent': bpy.props.FloatProperty(
            name="%", default=default_percent, min=0.1, max=100.0,
            description="Percentage of the original triangle count to keep for this LOD"),
        'simplify_mode': bpy.props.EnumProperty(
            name="Mode",
            description="Quality preset for this LOD: how aggressively it is "
                        "simplified. Careful keeps the most detail; Very "
                        "Aggressive pushes the triangle count much lower",
            items=MODE_ITEMS, default=default_mode, update=_on_mode_change),
        # Engine fields - set by the Mode and read by the generator. Not
        # editable, but drawn greyed in the Details mirror (_draw_pro_details),
        # so each one needs the tooltip it has in Pro.
        'target_error': bpy.props.FloatProperty(
            name="Target Error", default=preset['target_error'], min=0.0, max=1.0, precision=4,
            description="Max deviation, relative to mesh extents. Simplification "
                        "stops early if it would exceed this before reaching the "
                        "target percentage"),
        'lock_border': bpy.props.BoolProperty(
            name="Lock Open Edges", default=preset['lock_border'],
            description="Prevent open/boundary edges from moving during simplification"),
        'use_prune': bpy.props.BoolProperty(
            name="Prune (aggressive)", default=preset['use_prune'],
            description="meshopt_SimplifyPrune: lets the simplifier discard cheap "
                        "disconnected components instead of only collapsing "
                        "edges. Helps when the LOD stops well above its target"),
        'protect_uv_seams': bpy.props.BoolProperty(
            name="Protect UV Seams", default=preset['protect_uv_seams'],
            description="meshopt_SimplifyVertex_Protect: locks vertices whose UV "
                        "differs across a shared position, so Permissive "
                        "collapses everywhere except UV seams. Only used "
                        "together with Permissive"),
        # Off in every mode, as in Pro: material borders are far fewer than UV
        # seams, and protecting them costs locked vertices the LOD needs.
        'protect_material_borders': bpy.props.BoolProperty(
            name="Protect Material Borders",
            default=preset['protect_material_borders'],
            description="Same meshopt_SimplifyVertex_Protect flag, on vertices "
                        "whose material differs across a shared position. Far "
                        "fewer vertices than UV seams, so it costs much less. "
                        "Only used together with Permissive - without it "
                        "material borders are already kept"),
        'use_decimate_finish': bpy.props.BoolProperty(
            name="Finish with Decimate", default=preset['use_decimate_finish'],
            description="Reach the target percentage with Blender's Decimate "
                        "(Collapse) when meshoptimizer stops short. Distorts UVs "
                        "less than Permissive. Turns on Protect UV Seams and "
                        "uses the importance mask"),
        'use_permissive': bpy.props.BoolProperty(
            name="Permissive (aggressive)", default=preset['use_permissive'],
            description="meshopt_SimplifyPermissive: allows collapsing across "
                        "UV/normal seams while the error stays acceptable. Lower "
                        "triangle count for some UV distortion. Experimental "
                        "upstream"),
        'use_attributes': bpy.props.BoolProperty(
            name="Preserve UVs && Normals", default=preset['use_attributes'],
            description="meshopt_simplifyWithAttributes: UV seams and hard edges "
                        "enter the error metric as attribute discontinuities "
                        "instead of being locked"),
        'use_vertex_update': bpy.props.BoolProperty(
            name="Vertex Update (moves UVs, more aggressive)", default=preset['use_vertex_update'],
            description="meshopt_simplifyWithUpdate: moves vertex positions and "
                        "UVs to fit the new topology instead of only picking "
                        "among original vertices. Less distortion at aggressive "
                        "ratios, at the cost of some UV drift"),
        'normal_weight': bpy.props.FloatProperty(
            name="Normal Weight", default=preset['normal_weight'], min=0.0, soft_max=1.0, max=2.0,
            description="Weight of surface normals in the error metric. 0 = "
                        "shading may distort freely. meshoptimizer suggests "
                        "around 1.0"),
        'uv_weight': bpy.props.FloatProperty(
            name="UV Weight", default=preset['uv_weight'], min=0.0, soft_max=1.0, max=100.0,
            description="Weight of UV coordinates in the error metric. 0 = "
                        "texture may stretch freely. UVs are 0-1 while positions "
                        "are in scene units, so large meshes need values above 1 "
                        "(meshoptimizer suggests 10-100)"),
        'preprune_threshold': bpy.props.FloatProperty(
            name="Pre-prune", default=preset['preprune_threshold'], min=0.0, max=0.2, precision=3,
            description="meshopt_simplifyPrune as a pre-pass: drops disconnected "
                        "components smaller than this fraction of the mesh, "
                        "before the main simplification. 0 = off. Independent of "
                        "Target Error, unlike the Prune checkbox"),
        # Deliberately NOT in PRESET_FIELDS: no mode sets it, so switching Mode
        # leaves the user's choice alone. Only offered on the modes in
        # SMOOTH_NORMALS_MODES, and gated again at generation time - a setting
        # the panel hides must not keep applying.
        'use_smooth_normals': bpy.props.BoolProperty(
            name="Recalculate + Smooth", default=False,
            description="Discard the source normals and generate new ones from "
                        "the simplified geometry (meshoptimizer, experimental). "
                        "Edges meeting at a sharp angle stay hard. At very low "
                        "triangle counts the source normals no longer match the "
                        "geometry, which is what makes shading look dented"),
        # Exposed, unlike the relaxation strength: the right crease angle depends
        # on the model, and Light has no other way to change it. Also outside
        # PRESET_FIELDS, so switching Mode keeps the user's value.
        'smooth_crease_angle': bpy.props.FloatProperty(
            name="Crease Angle", default=SMOOTH_CREASE_ANGLE,
            min=0.0, max=math.pi, subtype='ANGLE',
            description="Edges whose faces meet at a sharper angle than this "
                        "stay hard when normals are recalculated. Lower keeps "
                        "more edges crisp; higher smooths more of them together"),
        'show_details': bpy.props.BoolProperty(
            name="Details", default=False,
            description="Show the advanced per-LOD settings for this LOD"),
    }
    # Only the self-hosted build draws the greyed Pro mirror, so only it needs
    # the fields to draw from - the store build carries none of them.
    if SHOW_PRO_TEASER:
        annotations.update(pro_only_annotations())
    return type(class_name, (bpy.types.PropertyGroup,), {'__annotations__': annotations})


LodSlotPropsLight1 = make_lod_slot_class("LodSlotPropsLight1", 50.0, 'CAREFUL')
LodSlotPropsLight2 = make_lod_slot_class("LodSlotPropsLight2", 20.0, 'STANDARD')
LodSlotPropsLight3 = make_lod_slot_class("LodSlotPropsLight3", 10.0, 'STANDARD')
LodSlotPropsLight4 = make_lod_slot_class("LodSlotPropsLight4", 5.0, 'AGGRESSIVE')
LodSlotPropsLight5 = make_lod_slot_class("LodSlotPropsLight5", 1.0, 'VERY_AGGRESSIVE')


LINEUP_PROP = "lodgen_lineup_orig"


def _lineup_restore(context):
    """Undo the 'Line Up LODs' arrangement: move every object that carries a
    stored original matrix back, and leave local view in any 3D viewport
    that's in it. Safe to call when the lineup isn't active."""
    props = context.scene.lodgen_light_props
    if not props.lineup_active:
        return
    for o in bpy.data.objects:
        stored = o.get(LINEUP_PROP)
        if stored is not None and len(stored) == 16:
            o.matrix_world = Matrix((stored[0:4], stored[4:8],
                                     stored[8:12], stored[12:16]))
            del o[LINEUP_PROP]
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            space = area.spaces.active
            if space.local_view is None:
                continue
            region = next((r for r in area.regions if r.type == 'WINDOW'), None)
            if region is None:
                continue
            try:
                with context.temp_override(window=window, area=area, region=region):
                    bpy.ops.view3d.localview(frame_selected=False)
            except Exception as exc:
                print(f"[LOD Generator] Could not leave local view: {exc}")
    props.lineup_active = False


def _on_lod_preview_change(self, context):
    """Distance-slider: 0 shows only lod_0, N shows only lod_N. Uses the
    exact same show/hide mechanism as the 'Only This LOD' buttons, so there
    is one single source of truth - no conflicting state between the two."""
    _lineup_restore(context)
    obj = context.active_object
    if obj is None:
        return
    m = match_lod_name(obj.name)
    base = m.group(1) if m else obj.name
    family = find_lod_family(base)
    target_idx = min(self.lod_preview, self.lod_count)
    if target_idx not in family:
        return
    for idx, o in family.items():
        o.hide_set(idx != target_idx)
        o.select_set(idx == target_idx)
    context.view_layer.objects.active = family[target_idx]


class LodGenPropsLight(bpy.types.PropertyGroup):
    lod_count: bpy.props.IntProperty(
        name="Number of LODs", default=3, min=1, max=MAX_LODS,
        description="How many LOD objects to generate")
    lod_preview: bpy.props.IntProperty(
        name="LOD Preview (distance)", default=0, min=0, max=MAX_LODS,
        description="Simulates moving away from the object: 0 = lod_0 (closest), "
                    "higher = further/more aggressive LODs. Same effect as the "
                    "'Only This LOD' buttons",
        update=_on_lod_preview_change)
    lod_1: bpy.props.PointerProperty(type=LodSlotPropsLight1)
    lod_2: bpy.props.PointerProperty(type=LodSlotPropsLight2)
    lod_3: bpy.props.PointerProperty(type=LodSlotPropsLight3)
    lod_4: bpy.props.PointerProperty(type=LodSlotPropsLight4)
    lod_5: bpy.props.PointerProperty(type=LodSlotPropsLight5)

    use_error_absolute: bpy.props.BoolProperty(
        name="Error Absolute (for multiple materials)", default=False,
        description="Treat Target Error as an absolute distance instead of "
                    "relative to mesh extents - gives more precise control for "
                    "very aggressive LODs, especially with multiple materials")
    merge_by_distance: bpy.props.BoolProperty(
        name="Merge by Distance", default=True,
        description="Weld coincident vertices on the result (Blender's Merge by "
                    "Distance). UVs and normals are stored per face-corner, so "
                    "welding does not blend them")
    merge_distance: bpy.props.FloatProperty(
        name="Merge Threshold", default=0.0001, min=0.0, max=0.01, precision=5,
        description="Keep this small - a large value can weld nearby but "
                    "intentionally separate geometry (e.g. thin gaps) together")
    lineup_active: bpy.props.BoolProperty(
        name="LOD Lineup Active", default=False,
        description="Internal state of the 'Line Up LODs' review mode")
    use_multi_uv: bpy.props.BoolProperty(
        name="Multiple UV Channels", default=False,
        description="Carry every UV channel onto the LODs, keeping names and "
                    "active/render flags. All of them enter the error metric "
                    "with the same UV Weight, so extra seams constrain "
                    "simplification. Off = only the active channel is copied")
    use_vcolor_importance: bpy.props.BoolProperty(
        name="Importance Mask", default=False,
        description="Bias simplification with a per-vertex importance map: "
                    "important areas cost more to collapse, so they keep more "
                    "detail. Pick the source with Importance Source. One "
                    "setting for every LOD here; SimplyFive Pro sets the mask "
                    "per LOD")
    vcolor_importance_weight: bpy.props.FloatProperty(
        name="Importance Strength", default=0.5, min=0.0, max=1.0,
        description="How much of the painted area is protected: the brightest "
                    "share of it is marked high-priority for meshoptimizer, so "
                    "1.0 covers everything painted and 0.5 the brighter half. "
                    "Not an absolute guarantee - very aggressive ratios can "
                    "still reach into those areas. The same strength applies to "
                    "every LOD here; SimplyFive Pro sets it per LOD, so a near "
                    "LOD can anchor a little and a distant one all of it")
    importance_source: bpy.props.EnumProperty(
        name="Importance Source", default='VCOLOR',
        description="Where the per-vertex importance mask is read from",
        items=[
            ('VCOLOR', "Vertex Color",
             "Luminance of the active color attribute (white = important)"),
            ('VGROUP', "Vertex Group",
             "Weights of a named vertex group (1 = important) - editable in "
             "Weight Paint, and never guessed, so bone weights on a rigged "
             "mesh are left alone"),
        ])
    importance_vgroup: bpy.props.StringProperty(
        name="Importance Group", default="",
        description="Vertex group whose weights drive the importance mask "
                    "(used only when Source = Vertex Group)")

    gpu_optimize: bpy.props.BoolProperty(
        name="Optimize for GPU", default=False,
        description="Reorder triangles and vertices the way a GPU reads them "
                    "(vertex cache, overdraw, fetch locality). Nothing moves in "
                    "space and no triangle is added or removed - only the order "
                    "in the file. Also applied to lod_0")

    # Written at generation time, read by the panel: both scans are whole-mesh
    # passes and must never run from draw().
    coincident_for: bpy.props.StringProperty(default="", options={'HIDDEN'})
    coincident_note: bpy.props.StringProperty(default="", options={'HIDDEN'})
    unwrapped_uv_note: bpy.props.StringProperty(default="", options={'HIDDEN'})
    blocking_uv_note: bpy.props.StringProperty(default="", options={'HIDDEN'})


# Hard-Lock is Pro-only, and Light's importance mask is one global setting
# rather than one per LOD - so its greyed row belongs next to that mask, not in
# the per-LOD mirror. Inert, and declared outside the class body for the same
# reason the slot fields are: the store build must carry no dead property.
if SHOW_PRO_TEASER:
    LodGenPropsLight.__annotations__['use_vcolor_lock'] = bpy.props.BoolProperty(
        name="Hard-Lock Above Threshold", default=False,
        description="Also lock every vertex above the threshold outright, so "
                    "it is never collapsed. Available in SimplyFive Pro - the "
                    "mask here is a weight, which very aggressive ratios can "
                    "still reach into")


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

# Source name -> scan. Both scans are whole-mesh passes, so they outlive the
# press that paid for them; _drop_stale_scans clears an entry the moment its
# geometry changes. Bounded because the keep mask is a byte per triangle.
_SOURCE_SCANS = {}
_SOURCE_SCANS_MAX = 8


@bpy.app.handlers.persistent
def _drop_stale_scans(scene, depsgraph):
    """is_updated_geometry fires for a mesh edited any way tested - operators,
    bmesh, raw foreach_set - and not for an untouched source when the LOD
    objects are created next to it."""
    if not _SOURCE_SCANS:
        return
    for upd in depsgraph.updates:
        if not upd.is_updated_geometry:
            continue
        name = getattr(upd.id, "name", None)
        _SOURCE_SCANS.pop(name, None)
        for key, scan in list(_SOURCE_SCANS.items()):
            if scan.get("mesh") == name:
                del _SOURCE_SCANS[key]


@bpy.app.handlers.persistent
def _drop_all_scans(*args):
    _SOURCE_SCANS.clear()


def new_source_scan(props, lod0):
    """Shape of the mesh both scans ran on, so simplify_object can tell whether
    their results still apply to what it is about to simplify."""
    me = lod0.data
    me.calc_loop_triangles()
    return {"tris": len(me.loop_triangles), "loops": len(me.loops),
            "uv_names": tuple(l.name for l in me.uv_layers),
            "mesh": me.name, "keep": None, "no_duplicates": False,
            "unwrapped": None, "coincident_note": "", "unwrapped_note": "",
            "checked": (get_pref('check_duplicate_faces', True),
                        get_pref('check_unwrapped_uv', True))}


def scan_coincident(props, base, lod0, scan=None):
    """Run on lod_0 at generation time and cached; the panel only reads. Keyed
    on base, not on lod0.name: resolve_lod0 falls back to the selected LOD when
    lod_0 is missing. Failure is non-fatal - a warning must never take a
    generation down."""
    props.coincident_for = base
    try:
        found = mesh_ops.find_coincident_faces(lod0.data)
    except Exception as exc:
        print(f"[LOD Generator] coincident-surface scan failed on "
              f"{lod0.name}: {exc}")
        props.coincident_note = ""
        return ""
    if not found:
        if scan is not None:
            scan["no_duplicates"] = True
        props.coincident_note = ""
        return ""
    if scan is not None:
        scan["keep"] = found["keep"]
    # Numbers only, like the tris/verts line in the panel: a formatted string
    # can never match a translations.py key.
    note = f"{found['triangles']} / {found['total']} tris in {found['places']} spots"
    props.coincident_note = note
    print(f"[LOD Generator] {lod0.name}: {note}. Materials: "
          f"{', '.join(found['materials'])}. Vertices shared by both copies "
          f"classify as Kind_Locked - these faces do not collapse at any "
          f"ratio without Permissive.")
    return note


def scan_unwrapped_uv(props, base, lod0, scan=None):
    """Cached alongside scan_coincident, same rules. Returns the names of the
    layers that can be dropped; layers that block but carry real coordinates
    go to blocking_uv_note and are only reported."""
    props.coincident_for = base
    props.blocking_uv_note = ""
    try:
        found = mesh_ops.find_unwrapped_uv_layers(lod0.data)
    except Exception as exc:
        print(f"[LOD Generator] UV scan failed on {lod0.name}: {exc}")
        props.unwrapped_uv_note = ""
        return ""
    if scan is not None:
        scan["unwrapped"] = frozenset(f["name"] for f in found if f["default"])
    if not found:
        props.unwrapped_uv_note = ""
        return ""
    for f in found:
        print(f"[LOD Generator] {lod0.name}: UV map '{f['name']}' locks "
              f"{100 * f['locked']:.0f}% of vertices with 3+ UVs. "
              + ("Never unwrapped - Blender's own per-face fill."
                 if f["default"] else
                 "Its coordinates are real, so it is reported only."))
    props.blocking_uv_note = ", ".join(f["name"] for f in found
                                       if not f["default"])
    note = ", ".join(f["name"] for f in found if f["default"])
    props.unwrapped_uv_note = note
    return note


def source_scan(props, base, lod0):
    """The scan for this source, computed once and reused until its geometry
    changes. Writes the panel's notes either way."""
    scan = _SOURCE_SCANS.get(lod0.name)
    fresh = new_source_scan(props, lod0)
    # "checked" is in the key: turning a check back on must rescan, or the
    # entry stored while it was off would answer for it.
    if scan is not None and all(
            scan.get(k) == fresh[k]
            for k in ("tris", "loops", "uv_names", "mesh", "checked")):
        props.coincident_for = base
        props.coincident_note = scan["coincident_note"]
        props.unwrapped_uv_note = scan["unwrapped_note"]
        return scan
    scan = fresh
    if scan["checked"][0]:
        scan["coincident_note"] = scan_coincident(props, base, lod0, scan)
    else:
        props.coincident_for = base
        props.coincident_note = ""
    if scan["checked"][1]:
        scan["unwrapped_note"] = scan_unwrapped_uv(props, base, lod0, scan)
    else:
        props.unwrapped_uv_note = ""
    _SOURCE_SCANS[lod0.name] = scan
    while len(_SOURCE_SCANS) > _SOURCE_SCANS_MAX:
        del _SOURCE_SCANS[next(iter(_SOURCE_SCANS))]
    return scan


def optimize_lod0(props, lod0):
    """lod_0 is the user's own object, not something we build, so the switch has
    to reach it separately or the heaviest mesh of the family ships in whatever
    order it happened to have. Runs before the scan: reordering afterwards would
    drop the entry that was just cached. Writes nothing when the mesh is already
    in order, which is what keeps a second press free."""
    if not props.gpu_optimize or lod0 is None or lod0.type != 'MESH':
        return
    try:
        if mesh_ops.reorder_object_for_gpu(lod0):
            print(f"[LOD Generator] {lod0.name} reordered for GPU")
    except Exception as exc:
        print(f"[LOD Generator] GPU order optimization skipped on "
              f"{lod0.name}: {exc}")


def generate_one_lod(context, lod0, base, i, slot, props, scan=None):
    """(Re)generate a single LOD, always replacing any existing object of the
    same name - no old versions are kept around. The source is always lod 0;
    each LOD's aggressiveness comes from its Mode preset and percentage."""
    name = lod_name(base, i)
    existing = bpy.data.objects.get(name)
    if existing is not None:
        bpy.data.objects.remove(existing, do_unlink=True)

    ratio = slot.percent / 100.0

    options = 0
    if slot.lock_border:
        options |= MESHOPT_LOCK_BORDER
    if slot.use_prune:
        options |= MESHOPT_PRUNE
    if slot.use_permissive:
        options |= native_build.MESHOPT_PERMISSIVE
    if props.use_error_absolute:
        options |= MESHOPT_ERROR_ABSOLUTE

    try:
        obj, before, after, result_error = simplify_object(
            context, lod0, ratio, slot.target_error, options,
            slot.use_attributes, slot.normal_weight, slot.uv_weight, name,
            props.merge_by_distance, props.merge_distance,
            use_vertex_update=slot.use_vertex_update,
            protect_uv_seams=slot.protect_uv_seams or slot.use_decimate_finish,
            protect_material_borders=slot.protect_material_borders,
            use_vcolor_importance=props.use_vcolor_importance,
            importance_weight=props.vcolor_importance_weight,
            preprune_threshold=slot.preprune_threshold,
            use_multi_uv=props.use_multi_uv,
            use_decimate_finish=slot.use_decimate_finish,
            importance_source=props.importance_source,
            importance_vgroup=props.importance_vgroup,
            # Gated on the mode, not just on the checkbox: the panel only shows
            # it for these modes, and a hidden setting must not still apply.
            use_smooth_normals=(slot.use_smooth_normals
                                and slot.simplify_mode in SMOOTH_NORMALS_MODES),
            smooth_crease_angle=slot.smooth_crease_angle,
            skip_unwrapped_uv=(get_pref('check_unwrapped_uv', True)
                               and get_pref('skip_unwrapped_uv', True)),
            drop_duplicates=(get_pref('check_duplicate_faces', True)
                             and get_pref('remove_duplicate_faces', True)),
            gpu_order=props.gpu_optimize,
            source_scan=scan,
            # preprune_budget / retarget_steps are left at their defaults (no
            # cap, no retry): the Limit Prune switch that drove them is Pro-only.
        )
    except Exception as exc:
        print(f"[LOD Generator] LOD {i} failed: {exc}")
        return None, 0, 0, 0.0
    # Achieved simplification error (normalized to source extents), stored on
    # the object so downstream LOD-switching logic can read one value off it.
    obj["lodgen_error"] = result_error
    return obj, before, after, result_error


class LODGENLIGHT_OT_generate(bpy.types.Operator):
    bl_idname = "lodgenlight.generate"
    bl_label = "Generate LODs"
    bl_description = "Create every configured LOD, from lod_0"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (native_available() and context.active_object is not None
                and context.active_object.type == 'MESH')

    def execute(self, context):
        _lineup_restore(context)
        # Leaving Edit Mode is mandatory, not cosmetic: regeneration removes
        # the old object, and removing one still in Edit Mode leaks its edit
        # mesh. Restored on every exit path, so a failed generation doesn't
        # silently drop the user out of Edit Mode either.
        editing = suspend_edit_mode(context)
        props = context.scene.lodgen_light_props
        base, lod0 = resolve_lod0(context.active_object)
        optimize_lod0(props, lod0)
        scan = source_scan(props, base, lod0)
        created = []

        failed = []
        for i in range(1, props.lod_count + 1):
            slot = getattr(props, f"lod_{i}")
            obj, before, after, err = generate_one_lod(context, lod0, base, i, slot,
                                                       props, scan)
            if obj is not None:
                created.append((obj, before, after, err))
            else:
                failed.append(i)

        if not created:
            self.report({'ERROR'}, "No LODs were generated.")
            resume_edit_mode(context, editing)
            return {'CANCELLED'}

        for o, _, _, _ in created:
            o.select_set(True)
        context.view_layer.objects.active = created[0][0]

        summary = ", ".join(f"{o.name} ({b}->{a} tris, err {e:.4f})" for o, b, a, e in created)
        # A skipped level must not read as success: the rest generated fine, but
        # that LOD is now missing and its previous object was already removed.
        if failed:
            self.report({'WARNING'},
                        f"LOD {', '.join(str(i) for i in failed)} not generated "
                        f"- see System Console. Generated {len(created)}: {summary}")
        else:
            self.report({'INFO'}, f"Generated {len(created)} LOD(s): {summary}")
        resume_edit_mode(context, editing)
        return {'FINISHED'}


class LODGENLIGHT_OT_generate_single(bpy.types.Operator):
    bl_idname = "lodgenlight.generate_single"
    bl_label = "Generate This LOD"
    bl_description = "Regenerate just this LOD from lod_0, replacing it (others untouched)"
    bl_options = {'REGISTER', 'UNDO'}
    lod_index: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        return (native_available() and context.active_object is not None
                and context.active_object.type == 'MESH')

    def execute(self, context):
        _lineup_restore(context)
        editing = suspend_edit_mode(context)   # see LODGENLIGHT_OT_generate
        props = context.scene.lodgen_light_props
        base, lod0 = resolve_lod0(context.active_object)
        optimize_lod0(props, lod0)
        scan = source_scan(props, base, lod0)
        slot = getattr(props, f"lod_{self.lod_index}")
        obj, before, after, err = generate_one_lod(context, lod0, base,
                                                   self.lod_index, slot, props, scan)
        if obj is None:
            self.report({'ERROR'}, f"LOD {self.lod_index} failed - see System Console.")
            resume_edit_mode(context, editing)
            return {'CANCELLED'}
        obj.select_set(True)
        context.view_layer.objects.active = obj
        self.report({'INFO'}, f"{obj.name}: {before} -> {after} tris, error {err:.4f}")
        resume_edit_mode(context, editing)
        return {'FINISHED'}


class LODGENLIGHT_OT_lineup(bpy.types.Operator):
    bl_idname = "lodgenlight.lineup"
    bl_label = "Line Up LODs"
    bl_description = ("Lay every existing LOD of this family out in a row, "
                       "isolated in local view (like pressing '/'), to compare "
                       "the progression side by side. Press again, move the "
                       "preview slider or use 'Only This LOD' to restore")

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        props = context.scene.lodgen_light_props
        if props.lineup_active:
            _lineup_restore(context)
            return {'FINISHED'}

        obj = context.active_object
        m = match_lod_name(obj.name)
        base = m.group(1) if m else obj.name
        family = find_lod_family(base)
        if len(family) < 2:
            self.report({'WARNING'}, "Nothing to line up - generate some LODs first.")
            return {'CANCELLED'}

        spacing = max((family[i].dimensions.x for i in family), default=0.0)
        if spacing <= 1e-6:
            spacing = 1.0
        spacing *= 1.2

        for o in context.view_layer.objects:
            o.select_set(False)
        for k, idx in enumerate(sorted(family)):
            o = family[idx]
            o.hide_set(False)
            o[LINEUP_PROP] = [c for row in o.matrix_world for c in row]
            mw = o.matrix_world.copy()
            mw.translation = mw.translation + Vector((k * spacing, 0.0, 0.0))
            o.matrix_world = mw
            o.select_set(True)
        context.view_layer.objects.active = family[min(family)]

        space = getattr(context, "space_data", None)
        if space is not None and space.type == 'VIEW_3D' and space.local_view is None:
            try:
                bpy.ops.view3d.localview(frame_selected=True)
            except Exception as exc:
                print(f"[LOD Generator] Could not enter local view: {exc}")

        props.lineup_active = True
        return {'FINISHED'}


class LODGENLIGHT_OT_isolate(bpy.types.Operator):
    bl_idname = "lodgenlight.isolate"
    bl_label = "Only This LOD"
    bl_description = "Hide every other LOD in this family. Use 'Show All LODs' to undo"
    lod_index: bpy.props.IntProperty()

    def execute(self, context):
        _lineup_restore(context)
        obj = context.active_object
        if obj is None:
            self.report({'WARNING'}, "No active object.")
            return {'CANCELLED'}
        m = match_lod_name(obj.name)
        base = m.group(1) if m else obj.name
        family = find_lod_family(base)
        target = family.get(self.lod_index)
        if target is None:
            self.report({'WARNING'}, f"LOD {self.lod_index} doesn't exist yet - generate it first.")
            return {'CANCELLED'}

        for idx, o in family.items():
            o.hide_set(idx != self.lod_index)

        for o in context.view_layer.objects:
            o.select_set(o == target)
        context.view_layer.objects.active = target
        context.scene.lodgen_light_props.lod_preview = self.lod_index
        return {'FINISHED'}


class LODGENLIGHT_OT_show_all(bpy.types.Operator):
    bl_idname = "lodgenlight.show_all"
    bl_label = "Show All LODs"
    bl_description = "Unhide every LOD in this object's family"

    def execute(self, context):
        obj = context.active_object
        if obj is None:
            self.report({'WARNING'}, "No active object.")
            return {'CANCELLED'}
        m = match_lod_name(obj.name)
        base = m.group(1) if m else obj.name
        family = find_lod_family(base)
        for o in family.values():
            o.hide_set(False)
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Update check
# ---------------------------------------------------------------------------

def _store_update_result(data):
    """Main thread, called by update_check's timer. Every field is treated as
    untrusted text: it comes off the network."""
    prefs = addon_prefs()
    if prefs is None:
        return
    prefs.last_update_check = str(int(time.time()))
    if not isinstance(data, dict):
        return
    version = str(data.get("version", ""))[:32]
    prefs.latest_version = version if update_check.parse_version(version) else ""
    url = str(data.get("url", ""))[:400]
    prefs.latest_url = url if url.startswith("https://") else URL_WEBSITE


def run_update_check(force=False):
    """False when nothing was started: switched off, checked recently, or one
    is already in flight."""
    prefs = addon_prefs()
    if prefs is None:
        return False
    if not force:
        if not prefs.check_updates:
            return False
        try:
            last = float(prefs.last_update_check or 0)
        except ValueError:
            last = 0.0
        if time.time() - last < update_check.CHECK_INTERVAL_DAYS * 86400:
            return False
    return update_check.start(update_check.VERSION_URL, _store_update_result)


def _deferred_update_check():
    """Off the register() path: a network call must never delay start-up."""
    run_update_check()
    return None


def update_available(prefs):
    return update_check.is_newer(prefs.latest_version, VERSION)


class LODGENLIGHT_OT_check_updates(bpy.types.Operator):
    bl_idname = "lodgenlight.check_updates"
    bl_label = "Check Now"
    bl_description = "Ask the product site whether a newer version exists"

    def execute(self, context):
        if not run_update_check(force=True):
            self.report({'INFO'}, "A check is already running.")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

# Public page describing the paid Pro version. Shown as a "Get Pro" button
# under the "available in Pro" teaser (self-hosted / GitHub build only,
# SHOW_PRO_TEASER). Leave empty to draw no button. Never put a raw payment
# address here - link to a real page.
PRO_URL = "https://zloy-pingvin.github.io/SimplyFive-Light/#pricing"

# Pro's per-LOD Details block, row for row, as one table. Each entry is
# (indent, requires, fields):
#   requires - attribute names that must all be truthy for the row to show, '!'
#              prefixed for "must be falsy". These are Pro's own conditions, so
#              the mirror hides exactly what Pro hides on the selected Mode: on
#              Careful, Permissive is off, so the two Protect rows are gone,
#              the way they are gone in Pro.
#   fields   - ((attr, kwargs), ...) drawn in one aligned row, the way Pro pairs
#              Normal/UV Weight; or a plain string for a label-only row.
# The order, nesting and conditions are Pro's, so a change on that side is a
# change to this table and nothing else.
#
# Rows Pro reveals only under a switch that no Light Mode turns on are absent
# rather than declared: see PRO_ONLY_SLOT_FIELDS. So are the rows whose feature
# Light already offers for real (Crease Angle, the Importance Mask fields) - a
# greyed twin of a working control would read as "not in the free version", the
# opposite of the truth.
PRO_DETAIL_ROWS = (
    (0, (), (("use_previous_lod", {}),)),
    (0, (), (("target_error", {}),)),
    (0, (), (("preprune_threshold", {"slider": True}),)),
    (0, (), (("lock_border", {}),)),
    (0, (), (("use_prune", {}),)),
    # Pro shows it whenever either prune bites: "use_prune or preprune > 0".
    # In every Light Mode the two coincide, so one gate is enough - verify_all
    # asserts that, so a Mode that breaks the pairing cannot slip through.
    (1, ("use_prune",), (("limit_prune", {}),)),
    (0, (), (("use_permissive", {}),)),
    # Pro gates both on Permissive + attributes: the seam lock is built from
    # UVs, so without them there is nothing to protect. And when the Decimate
    # finish is on it forces seam protection, so Pro replaces the checkbox with
    # a notice on that same row - VERY_AGGRESSIVE_ALT is where this shows.
    (1, ("use_permissive", "use_attributes", "!use_decimate_finish"),
     (("protect_uv_seams", {}),)),
    (1, ("use_permissive", "use_attributes", "use_decimate_finish"),
     "Protect UV Seams: on (Decimate finish)"),
    (1, ("use_permissive", "use_attributes"),
     (("protect_material_borders", {}),)),
    (0, (), (("use_decimate_finish", {}),)),
    (0, (), (("use_attributes", {}),)),
    (1, ("use_attributes",), (("normal_weight", {}), ("uv_weight", {}))),
    (0, (), (("normals_mode", {}),)),
    (0, ("use_attributes",), (("use_vertex_update", {}),)),
    (0, (), (("regularize_mode", {}),)),
    (0, ("use_attributes",), (("blend_colors_meshopt", {"slider": True}),)),
)

# Only meaningful from lod 2 on, exactly as in Pro.
PRO_DETAIL_FROM_LOD2 = {"use_previous_lod"}


def _pro_row_visible(slot, requires):
    """Pro's own show/hide conditions, read off the slot. The twelve real engine
    fields are what drive these, so the mirror follows the selected Mode."""
    for name in requires:
        want = not name.startswith('!')
        if bool(getattr(slot, name.lstrip('!'))) != want:
            return False
    return True


def _draw_pro_details(layout, slot, lod_index):
    """Pro's per-LOD panel, drawn greyed: the paid version's controls shown
    rather than listed. The twelve engine fields Light already keeps per slot
    are real, so they display the values this LOD is actually generated with
    and decide which rows appear; the rest are the inert declarations in
    pro_only_annotations().

    Only drawn in the self-hosted build (SHOW_PRO_TEASER); the store build
    leaves it out entirely. The "Get Pro" button goes on the parent layout,
    NOT inside the box: the box has enabled=False, and a button inside it
    would be unclickable."""
    box = layout.box()
    box.enabled = False
    box.label(text="Per-LOD settings - available in Pro", icon='LOCKED')
    for indent, requires, fields in PRO_DETAIL_ROWS:
        if not _pro_row_visible(slot, requires):
            continue
        if isinstance(fields, str):
            row = box.row(align=True)
            if indent:
                row.separator(factor=1.5 * indent)
            row.label(text=fields, icon='INFO')
            continue
        fields = tuple((a, kw) for a, kw in fields
                       if lod_index >= 2 or a not in PRO_DETAIL_FROM_LOD2)
        if not fields:
            continue
        row = box.row(align=True)
        if indent:
            row.separator(factor=1.5 * indent)
        for attr, kwargs in fields:
            row.prop(slot, attr, **kwargs)
    if PRO_URL:
        layout.operator("wm.url_open", text="Get SimplyFive Pro",
                        icon='UNLOCKED').url = PRO_URL


class VIEW3D_PT_lod_generator(bpy.types.Panel):
    # Built from VERSION, never typed twice: the header is the fastest way to
    # tell which build is installed. Not a translation key either - a computed
    # label could never match one.
    bl_label = "SimplyFive Light %s" % '.'.join(str(x) for x in VERSION)
    bl_idname = "VIEW3D_PT_lod_generator_light"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "LODS"

    def draw(self, context):
        layout = self.layout
        props = context.scene.lodgen_light_props
        obj = context.active_object

        if not native_available():
            box = layout.box()
            box.label(text="meshoptimizer: not built yet", icon='ERROR')
            box.label(text="Build it in Edit > Preferences > Add-ons", icon='INFO')

        if not (obj and obj.type == 'MESH'):
            layout.label(text="Select a mesh to begin.", icon='INFO')
            return

        layout.label(text=f"Active: {obj.name}")
        tri_count = mesh_tri_count(obj.data)
        layout.label(text=f"  {tri_count} tris / {len(obj.data.vertices)} verts")

        m = match_lod_name(obj.name)
        base = m.group(1) if m else obj.name
        lod0_name = lod_name(base, 0)

        # Cached by the scans at generation time - they are whole-mesh passes
        # and far too slow to run from draw(). Keyed on base, so a note stays
        # visible across the family and hides when another object is selected.
        if props.blocking_uv_note and props.coincident_for == base:
            warn = layout.box()
            warn.label(text="UV map blocks simplification", icon='ERROR')
            warn.label(text=props.blocking_uv_note)
            warn.label(text="Every face is its own island, which locks")
            warn.label(text="the mesh. Left as is - it holds real data.")

        if props.unwrapped_uv_note and props.coincident_for == base:
            warn = layout.box()
            if get_pref('skip_unwrapped_uv', True):
                warn.label(text="UV map not unwrapped: ignored", icon='INFO')
                warn.label(text=props.unwrapped_uv_note)
                warn.label(text="Left out of simplification, copied to")
                warn.label(text="the LOD as is.")
            else:
                warn.label(text="UV map not unwrapped", icon='ERROR')
                warn.label(text=props.unwrapped_uv_note)
                warn.label(text="Every face holds the whole 0-1 square,")
                warn.label(text="which locks the mesh. Unwrap it.")

        if props.coincident_note and props.coincident_for == base:
            warn = layout.box()
            if get_pref('remove_duplicate_faces', True):
                warn.label(text="Duplicated surfaces dropped", icon='INFO')
                warn.label(text=props.coincident_note)
                warn.label(text="One copy per spot was kept. A material")
                warn.label(text="used only by the copy is gone with it.")
            else:
                warn.label(text="Duplicated surfaces found", icon='ERROR')
                warn.label(text=props.coincident_note)
                warn.label(text="Locked by meshoptimizer, these faces")
                warn.label(text="never simplify. Delete one copy.")

        preview_row = layout.row(align=True)
        preview_row.prop(props, "lod_preview", slider=True)
        preview_row.operator("lodgenlight.lineup", text="", icon='MOD_ARRAY',
                             depress=props.lineup_active)

        layout.label(text=lod0_name, icon='MESH_DATA')
        row = layout.row(align=True)
        row.scale_y = 1.5
        family0 = find_lod_family(base)
        lod0_obj = family0.get(0)
        lod0_isolated = (lod0_obj is not None and not lod0_obj.hide_get() and
                          all(o.hide_get() for idx, o in family0.items() if idx != 0))
        op = row.operator("lodgenlight.isolate", text="Only This LOD", icon='HIDE_OFF',
                           depress=lod0_isolated)
        op.lod_index = 0
        row.operator("lodgenlight.show_all", text="Show All LODs", icon='RENDERLAYERS')

        layout.separator()
        col = layout.column(align=True)
        col.prop(props, "lod_count")

        family = family0  # already scanned above; don't rescan every redraw

        for i in range(1, props.lod_count + 1):
            slot = getattr(props, f"lod_{i}")
            box = layout.box()
            header = box.row(align=True)
            header.label(text=lod_name(base, i))
            header.prop(slot, "percent", text="%")

            lod_obj = family.get(i)
            lod_exists = lod_obj is not None
            # "Active" = this LOD is the only visible one in its family.
            is_isolated = lod_exists and not lod_obj.hide_get() and all(
                o.hide_get() for idx, o in family.items() if idx != i)

            big_row = box.row(align=True)
            big_row.scale_y = 1.5
            op = big_row.operator("lodgenlight.isolate", text="Only This LOD",
                                   icon='HIDE_OFF', depress=is_isolated)
            op.lod_index = i
            gen_col = big_row.row(align=True)
            gen_col.alert = not lod_exists  # red/warning tint until generated
            gen_op = gen_col.operator("lodgenlight.generate_single", text="Generate This LOD",
                                       icon='FILE_REFRESH' if lod_exists else 'ADD')
            gen_op.lod_index = i

            box.prop(slot, "simplify_mode")
            # Only where it does something; generation checks the same set, so a
            # value left over from another mode cannot apply unseen.
            if slot.simplify_mode in SMOOTH_NORMALS_MODES:
                box.prop(slot, "use_smooth_normals")
                if slot.use_smooth_normals:
                    box.prop(slot, "smooth_crease_angle")
            if SHOW_PRO_TEASER:
                box.prop(slot, "show_details",
                         icon='TRIA_DOWN' if slot.show_details else 'TRIA_RIGHT', emboss=False)
                if slot.show_details:
                    _draw_pro_details(box, slot, i)

        # The importance mask first, in a column of its own with a separator on
        # either side: it is a workflow of its own (paint a mask, then pick how
        # much of it to anchor), not another output option like the rest below.
        layout.separator()
        mask = layout.column(align=True)
        mask.prop(props, "use_vcolor_importance")
        if props.use_vcolor_importance:
            mask.prop(props, "importance_source")
            if props.importance_source == 'VGROUP':
                obj = context.active_object
                if obj is not None:
                    mask.prop_search(props, "importance_vgroup", obj, "vertex_groups")
                else:
                    mask.prop(props, "importance_vgroup")
            mask.prop(props, "vcolor_importance_weight", slider=True)
            # Pro-only, drawn greyed right under the mask it belongs to. Its
            # Lock Threshold row is not drawn: in Pro that row appears only once
            # Hard-Lock is on, and a greyed checkbox can never turn it on.
            if SHOW_PRO_TEASER:
                lock = mask.row()
                lock.enabled = False
                lock.prop(props, "use_vcolor_lock")

        layout.separator()
        col = layout.column(align=True)
        col.prop(props, "use_error_absolute")
        col.prop(props, "merge_by_distance")
        if props.merge_by_distance:
            col.prop(props, "merge_distance")

        col.prop(props, "use_multi_uv")

        # The source checks used to sit here; they are workflow preferences, so
        # they live in Edit > Preferences > Add-ons now, as in Pro.
        # Hidden outright when the bundled library predates the reordering
        # calls: a switch that silently does nothing must not be offered.
        if native_build.has_gpu_optimize():
            col.prop(props, "gpu_optimize")

        layout.separator()
        layout.operator("lodgenlight.generate", icon='MOD_DECIM')



# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    LodGenAddonPreferences,
    LodSlotPropsLight1,
    LodSlotPropsLight2,
    LodSlotPropsLight3,
    LodSlotPropsLight4,
    LodSlotPropsLight5,
    LodGenPropsLight,
    LODGENLIGHT_OT_check_updates,
    LODGENLIGHT_OT_generate,
    LODGENLIGHT_OT_generate_single,
    LODGENLIGHT_OT_lineup,
    LODGENLIGHT_OT_isolate,
    LODGENLIGHT_OT_show_all,
    VIEW3D_PT_lod_generator,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.lodgen_light_props = bpy.props.PointerProperty(type=LodGenPropsLight)
    bpy.app.translations.register(__name__, translations._build_translations_dict())
    # Three layers, all three needed: geometry edits, and file load / undo /
    # redo, which replace datablocks wholesale without a depsgraph update we
    # can read.
    _SOURCE_SCANS.clear()
    if _drop_stale_scans not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_drop_stale_scans)
    for handlers in (bpy.app.handlers.load_post, bpy.app.handlers.undo_post,
                     bpy.app.handlers.redo_post):
        if _drop_all_scans not in handlers:
            handlers.append(_drop_all_scans)
    # Deferred: a network timeout must never sit in the way of Blender starting
    # up. run_update_check() re-reads the switch when it fires, so turning the
    # check off is honoured even though the timer is always armed.
    if not bpy.app.timers.is_registered(_deferred_update_check):
        bpy.app.timers.register(_deferred_update_check, first_interval=5.0)
    try_load_native()


def unregister():
    update_check.cancel()
    if bpy.app.timers.is_registered(_deferred_update_check):
        bpy.app.timers.unregister(_deferred_update_check)
    for handlers in (bpy.app.handlers.load_post, bpy.app.handlers.undo_post,
                     bpy.app.handlers.redo_post):
        if _drop_all_scans in handlers:
            handlers.remove(_drop_all_scans)
    if _drop_stale_scans in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_drop_stale_scans)
    _SOURCE_SCANS.clear()
    bpy.app.translations.unregister(__name__)
    del bpy.types.Scene.lodgen_light_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
