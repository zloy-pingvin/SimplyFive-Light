# A Blender add-on that generates a set of LOD meshes (Level of Detail) from the active object, using the meshoptimizer library ( by Arseny Kapoulkine, distributed under the MIT License)   
# For each mesh you can create up to 5 simplified versions with individual aggressiveness settings;
# simplification can take UV unwrapping, normals, vertex colors (as an importance map), and materials into account.
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 zloy_pingvin

bl_info = {
    "name": "SimplyFive Light (lod generator)",
    "author": "zloy_pingvin",
    "version": (1, 1, 2),
    "blender": (5, 0, 0),
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
from .mesh_ops import (
    MESHOPT_LOCK_BORDER, MESHOPT_SPARSE, MESHOPT_ERROR_ABSOLUTE, MESHOPT_PRUNE,
    simplify_object,
)
from .native_build import native_available, try_load_native
import re

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

DEFAULT_LOD_SUFFIX = "_lod_"

_lod_re_cache = {}


def get_lod_suffix():
    """The user-configured text between the base object name and the LOD
    index (AddonPreferences). Falls back to the default during early
    registration or if the user empties the field."""
    try:
        suffix = bpy.context.preferences.addons[__name__].preferences.lod_suffix
    except Exception:
        return DEFAULT_LOD_SUFFIX
    return suffix if suffix else DEFAULT_LOD_SUFFIX


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
    'CAREFUL': dict(lock_border=True, use_sparse=False,
                     use_prune=False, use_permissive=False, protect_uv_seams=False,
                     use_attributes=True, use_vertex_update=False,
                     normal_weight=0.5, uv_weight=0.5, target_error=0.02,
                     preprune_threshold=0.0),
    'STANDARD': dict(lock_border=True, use_sparse=False,
                      use_prune=False, use_permissive=False, protect_uv_seams=False,
                      use_attributes=True, use_vertex_update=True,
                      normal_weight=0.5, uv_weight=0.5, target_error=0.15,
                     preprune_threshold=0.0),
    'AGGRESSIVE': dict(lock_border=False, use_sparse=True,
                        use_prune=True, use_permissive=True, protect_uv_seams=True,
                        use_attributes=True, use_vertex_update=True,
                        normal_weight=0.2, uv_weight=0.2, target_error=0.3,
                     preprune_threshold=0.02),
    'VERY_AGGRESSIVE': dict(lock_border=False, use_sparse=True,
                             use_prune=True, use_permissive=True, protect_uv_seams=False,
                             use_attributes=True, use_vertex_update=True,
                             normal_weight=0.01, uv_weight=1.0, target_error=0.5,
                     preprune_threshold=0.07),
}

# The fields a Mode preset writes onto a LOD slot when selected. These drive
# the actual meshoptimizer call. The Light UI does not expose them for manual
# per-LOD editing (that fine-tuning is a Pro feature), so a slot's effective
# values always come straight from its selected Mode.
PRESET_FIELDS = [
    "lock_border", "use_sparse", "use_prune", "use_permissive", "protect_uv_seams",
    "use_attributes", "use_vertex_update", "normal_weight", "uv_weight",
    "target_error", "preprune_threshold",
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

    lod_suffix: bpy.props.StringProperty(
        name="LOD Name Suffix", default=DEFAULT_LOD_SUFFIX,
        description="Text between the base object name and the LOD index "
                    "(e.g. '_lod_' gives 'Cube_lod_1'). Changing it does not "
                    "rename existing LODs - objects named with the old suffix "
                    "are no longer recognized as part of a LOD family")

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Add-on version: {'.'.join(str(x) for x in bl_info['version'])}")

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
     "Permissive + Prune + Sparse + protected UV seams, higher Target Error"),
    ('VERY_AGGRESSIVE', "Very Aggressive",
     "Like Aggressive but UV seams not protected and attribute weights are "
     "very low - pushes triangle count much lower, more UV drift"),
]


def make_lod_slot_class(class_name, default_percent, default_mode):
    """Each LOD slot gets its own PropertyGroup subclass so it can start with
    a different default percentage/Mode than the others. The engine fields
    below are written by the selected Mode (see _on_mode_change) and read by
    the generator; the Light panel does not expose them for manual per-LOD
    editing (that fine-tuning is a Pro feature)."""
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
        # Engine fields - set by the Mode, read by the generator, not drawn.
        'target_error': bpy.props.FloatProperty(
            name="Target Error", default=preset['target_error'], min=0.0, max=1.0, precision=4),
        'lock_border': bpy.props.BoolProperty(
            name="Lock Open Edges", default=preset['lock_border']),
        'use_sparse': bpy.props.BoolProperty(
            name="Sparse", default=preset['use_sparse']),
        'use_prune': bpy.props.BoolProperty(
            name="Prune (aggressive)", default=preset['use_prune']),
        'protect_uv_seams': bpy.props.BoolProperty(
            name="Protect UV Seams", default=preset['protect_uv_seams']),
        'use_permissive': bpy.props.BoolProperty(
            name="Permissive (aggressive)", default=preset['use_permissive']),
        'use_attributes': bpy.props.BoolProperty(
            name="Preserve UVs && Normals", default=preset['use_attributes']),
        'use_vertex_update': bpy.props.BoolProperty(
            name="Vertex Update (moves UVs, more aggressive)", default=preset['use_vertex_update']),
        'normal_weight': bpy.props.FloatProperty(
            name="Normal Weight", default=preset['normal_weight'], min=0.0, soft_max=1.0, max=2.0),
        'uv_weight': bpy.props.FloatProperty(
            name="UV Weight", default=preset['uv_weight'], min=0.0, soft_max=1.0, max=100.0),
        'preprune_threshold': bpy.props.FloatProperty(
            name="Pre-prune", default=preset['preprune_threshold'], min=0.0, max=0.2, precision=3),
        'show_details': bpy.props.BoolProperty(
            name="Details", default=False,
            description="Show the advanced per-LOD settings for this LOD"),
    }
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
                    "'Only This LOD' buttons below",
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
        description="Weld coincident-position vertices on the result (Blender's "
                    "own Merge by Distance). Safe for UV seams - UVs/normals are "
                    "stored per face-corner, not per vertex, so welding topology "
                    "doesn't blend or lose them. Keep the threshold small")
    merge_distance: bpy.props.FloatProperty(
        name="Merge Threshold", default=0.0001, min=0.0, max=0.01, precision=5,
        description="Keep this small - a large value can weld nearby but "
                    "intentionally separate geometry (e.g. thin gaps) together")
    lineup_active: bpy.props.BoolProperty(
        name="LOD Lineup Active", default=False,
        description="Internal state of the 'Line Up LODs' review mode")
    use_multi_uv: bpy.props.BoolProperty(
        name="Multiple UV Channels", default=False,
        description="Carry every UV channel of the source mesh (not just the "
                    "active one) onto the LODs, keeping the original layer "
                    "names and active/render flags. All channels count in the "
                    "error metric with the same UV Weight. Off = only the "
                    "active UV channel is kept and other channels are not "
                    "copied. On = geometric quality can drop slightly at the "
                    "same percentage, because extra UV seams (e.g. lightmap "
                    "islands in UV2) constrain simplification")
    use_vcolor_importance: bpy.props.BoolProperty(
        name="Use Vertex Color as Importance", default=False,
        description="Read the active vertex color layer as a per-vertex "
                    "importance map (luminance: white = important, black = "
                    "unimportant) for every LOD. Important areas become "
                    "costlier to collapse, so they keep more detail. Paint it "
                    "with Blender's Vertex Paint mode")
    vcolor_importance_weight: bpy.props.FloatProperty(
        name="Importance Strength", default=0.5, min=0.0, max=1.0,
        description="How strongly vertex color importance biases simplification. "
                    "This is a soft weight (a penalty in the error metric), not "
                    "a hard guarantee - very aggressive ratios may still touch "
                    "important areas")


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

def generate_one_lod(context, lod0, base, i, slot, props):
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
    if slot.use_sparse:
        options |= MESHOPT_SPARSE
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
            protect_uv_seams=slot.protect_uv_seams,
            use_vcolor_importance=props.use_vcolor_importance,
            importance_weight=props.vcolor_importance_weight,
            preprune_threshold=slot.preprune_threshold,
            use_multi_uv=props.use_multi_uv,
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
        props = context.scene.lodgen_light_props
        base, lod0 = resolve_lod0(context.active_object)
        created = []

        for i in range(1, props.lod_count + 1):
            slot = getattr(props, f"lod_{i}")
            obj, before, after, err = generate_one_lod(context, lod0, base, i, slot, props)
            if obj is not None:
                created.append((obj, before, after, err))

        if not created:
            self.report({'ERROR'}, "No LODs were generated.")
            return {'CANCELLED'}

        for o, _, _, _ in created:
            o.select_set(True)
        context.view_layer.objects.active = created[0][0]

        summary = ", ".join(f"{o.name} ({b}->{a} tris, err {e:.4f})" for o, b, a, e in created)
        self.report({'INFO'}, f"Generated {len(created)} LOD(s): {summary}")
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
        props = context.scene.lodgen_light_props
        base, lod0 = resolve_lod0(context.active_object)
        slot = getattr(props, f"lod_{self.lod_index}")
        obj, before, after, err = generate_one_lod(context, lod0, base, self.lod_index, slot, props)
        if obj is None:
            self.report({'ERROR'}, f"LOD {self.lod_index} failed - see System Console.")
            return {'CANCELLED'}
        obj.select_set(True)
        context.view_layer.objects.active = obj
        self.report({'INFO'}, f"{obj.name}: {before} -> {after} tris, error {err:.4f}")
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
# Panel
# ---------------------------------------------------------------------------

# Public page describing the paid Pro version. Shown as a "Get Pro" button in
# the self-hosted / GitHub build only (SHOW_PRO_TEASER). Leave empty to draw
# no button. Never put a raw crypto address here - link to a real payment page.
PRO_URL = ""

# Advanced per-LOD controls that live in Pro. Listed in the greyed teaser so
# self-hosted users can see what the paid version adds.
PRO_LOD_FEATURES = (
    "Per-LOD Target Error",
    "Lock Border / Sparse / Prune",
    "Permissive + Protect UV Seams",
    "Vertex Update, Normal / UV Weight",
    "Sloppy (topology-ignoring)",
    "Regularize",
    "Recalculate + Auto Smooth",
    "Build from Previous LOD (chained)",
    "Vertex Color hard-lock",
)


def _draw_pro_teaser(layout, features):
    """Greyed 'available in Pro' block. Only drawn in the self-hosted build
    (SHOW_PRO_TEASER on); the store build hides it entirely for a clean UI."""
    box = layout.box()
    box.enabled = False
    box.label(text="Advanced - available in Pro", icon='LOCKED')
    col = box.column(align=True)
    for feat in features:
        col.label(text=feat, icon='DOT')


class VIEW3D_PT_lod_generator(bpy.types.Panel):
    bl_label = "SimplyFive Light"
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
        row.operator("lodgenlight.show_all", text="Show All LODs", icon='HIDE_OFF')
        op = row.operator("lodgenlight.isolate", text="Only This LOD", icon='HIDE_ON',
                           depress=lod0_isolated)
        op.lod_index = 0

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
            if SHOW_PRO_TEASER:
                box.prop(slot, "show_details",
                         icon='TRIA_DOWN' if slot.show_details else 'TRIA_RIGHT', emboss=False)
                if slot.show_details:
                    _draw_pro_teaser(box, PRO_LOD_FEATURES)

        layout.separator()
        col = layout.column(align=True)
        col.prop(props, "use_error_absolute")
        col.prop(props, "merge_by_distance")
        if props.merge_by_distance:
            col.prop(props, "merge_distance")

        col.prop(props, "use_multi_uv")

        col.prop(props, "use_vcolor_importance")
        if props.use_vcolor_importance:
            col.prop(props, "vcolor_importance_weight", slider=True)
            # Hard-lock above a threshold is a Pro feature; greyed teaser only,
            # shown here (under importance) just like it sits in Pro.
            if SHOW_PRO_TEASER:
                lock_row = col.row()
                lock_row.enabled = False
                lock_row.label(text="Hard-Lock Above Threshold (Pro)", icon='LOCKED')

        layout.separator()
        layout.operator("lodgenlight.generate", icon='MOD_DECIM')

        if SHOW_PRO_TEASER and PRO_URL:
            layout.separator()
            layout.operator("wm.url_open", text="Get SimplyFive Pro",
                            icon='FUND').url = PRO_URL


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
    try_load_native()


def unregister():
    bpy.app.translations.unregister(__name__)
    del bpy.types.Scene.lodgen_light_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
