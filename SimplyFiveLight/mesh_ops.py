"""Mesh <-> numpy buffers, and the actual calls into the compiled
meshoptimizer library (native_build._native_lib). Reads native_build's
mutable state through the module (native_build.X), never via 'from
native_build import X', since that would freeze in whatever value X had at
import time - before try_load_native() has actually set it.
"""

import bpy
import ctypes
import math
import numpy as np

from . import native_build
from .native_build import c_float_p, c_uint_p, c_ubyte_p


# Temporary vertex group used to feed the importance mask to Blender's
# Decimate (Finish with Decimate); always removed again after the modifier.
DECIMATE_IMPORTANCE_GROUP = "SF_DecimateImportance"


class SimplifyEmpty(Exception):
    """The simplifier returned no triangles at all. Prune deletes whole
    disconnected components once the error budget covers them, so a large
    Target Error can take the last one with it."""


def get_evaluated_mesh(context, obj):
    depsgraph = context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    me = eval_obj.to_mesh()
    return eval_obj, me


def mesh_to_position_buffers(me):
    me.calc_loop_triangles()
    positions = np.empty((len(me.vertices), 3), dtype=np.float32)
    me.vertices.foreach_get("co", positions.ravel())
    tris = me.loop_triangles
    flat = np.empty(len(tris) * 3, dtype=np.int32)
    tris.foreach_get("vertices", flat)
    indices = flat.astype(np.uint32)
    return positions, indices


def read_vertex_group_weights(obj, me, group_name):
    """Per-vertex weights of a named vertex group as a 0-1 array (1 =
    important), or None if the group doesn't exist. Vertex groups live on the
    object while the weights live in the mesh, so both must come from the
    same evaluated pair. There is no foreach_get for deform weights, hence
    the explicit loop - it is cheaper than the per-loop pass this feeds."""
    group = obj.vertex_groups.get(group_name) if group_name else None
    if group is None:
        return None
    index = group.index
    weights = np.zeros(len(me.vertices), dtype=np.float32)
    for i, vert in enumerate(me.vertices):
        for g in vert.groups:
            if g.group == index:
                weights[i] = g.weight
                break
    return weights


def _lum(rgba):
    """Luminance of an (N, 4) RGBA block.

    Accumulated in float64 and rounded once, like the per-element version
    this replaces: in float32 the last bit differs on a few vertices, and the
    importance mask is a cost weight, so that decides ties inside
    meshoptimizer and moves the result by a triangle or two."""
    return (0.2126 * rgba[:, 0].astype(np.float64)
            + 0.7152 * rgba[:, 1].astype(np.float64)
            + 0.0722 * rgba[:, 2].astype(np.float64))


def _read_color_layer(layer):
    """A color attribute's values as (N, 4) float32, one row per element of
    its own domain (loops for CORNER, vertices for POINT)."""
    buf = np.empty(len(layer.data) * 4, dtype=np.float32)
    layer.data.foreach_get("color", buf)
    return buf.reshape(-1, 4)


def source_is_flat_shaded(me):
    """True when every face is flat and there are no custom split normals.

    On such a mesh a corner normal is just its own face normal, so keying the
    dedup on it splits practically every corner into its own vertex - on a
    22M-triangle scan, 66M vertices instead of 11M, which costs both the
    buffer build and meshoptimizer itself several times over for information
    the geometry already carries.

    Attributes are matched while iterating rather than by name lookup, for the
    reason spelled out in deselect_mesh_elements."""
    # has_custom_normals, not a 'custom_normal' entry in me.attributes: in 4.2
    # they sit in a legacy layer and never show up there, so scanning the
    # attributes calls a flat mesh that carries them flat and drops them - a
    # hard-surface model then arrives with no shading at all, silently.
    if getattr(me, "has_custom_normals", False):
        return False
    sharp = None
    for attr in me.attributes:
        if attr.name == "custom_normal":
            return False
        if attr.name == "sharp_face":
            sharp = attr
    if sharp is None or not len(me.polygons) or len(sharp.data) != len(me.polygons):
        return False
    flags = np.empty(len(sharp.data), dtype=bool)
    sharp.data.foreach_get("value", flags)
    return bool(flags.all())


def repack_flat_custom_normals(me):
    """Re-pack a flat source's custom split normals against a smooth base.

    They are stored relative to each corner's computed normal, which on a flat
    face is the face normal - a different one per corner. One intended normal
    then decodes to a slightly different vector per corner, so the dedup key
    sees almost as many vertices as corners and nothing can collapse: measured
    on a flat-shaded scan, 1439312 keyed vertices against 254012 positions, and
    the LOD came back the size of the source. Reading the decoded normals and
    writing them back over a smooth base costs under 0.6 degrees anywhere.

    Only for the mesh from to_mesh(), which is a copy - never the user's own.
    Returns True when it changed anything."""
    if not getattr(me, "has_custom_normals", False) or not len(me.polygons):
        return False
    smooth = np.empty(len(me.polygons), dtype=bool)
    me.polygons.foreach_get("use_smooth", smooth)
    if smooth.all():
        return False
    keep = np.empty(len(me.loops) * 3, dtype=np.float32)
    me.corner_normals.foreach_get("vector", keep)
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), dtype=np.int32))
    me.update()
    me.normals_split_custom_set(keep.reshape(-1, 3))
    return True


def mesh_to_attribute_buffers(me, use_multi_uv=False, vgroup_weights=None,
                               key_normals=True):
    """Per-loop dedup, like a GPU vertex buffer: every unique
    (vertex, normal, uv, material) becomes its own entry. meshoptimizer's
    simplifyWithAttributes is specifically designed to handle the resulting
    attribute discontinuities (seams) gracefully as part of its cost metric,
    rather than needing them locked or treated as hard mesh boundaries.
    Material ID is baked into the dedup key (not passed to the simplifier
    itself) per meshoptimizer's documented multi-material approach: this
    makes material boundaries implicit mesh boundaries that survive
    simplification automatically (protect them via vertex_lock when using
    Permissive, since that mode explicitly allows crossing such boundaries).

    Also captures a per-vertex 'importance' scalar (0-1): vgroup_weights when
    a vertex group is used as the mask, else the luminance of the active
    color attribute if present. Higher = more important = should be
    simplified less. Not part of the dedup key (it's guidance, not topology).

    use_multi_uv=False: only the active UV layer is captured, other channels
    are dropped. True: every UV layer is captured - all of them go into the
    dedup key (a seam existing only in UV2 must still split vertices there,
    or its values get corrupted at that seam) and into the returned uvs
    array, whose shape becomes (N, 2*num_layers). Either way the returned
    uv_info dict records the captured layers' original names and
    active/active_render indices so the rebuilt LOD mesh restores them."""
    me.calc_loop_triangles()
    if use_multi_uv:
        uv_layers = list(me.uv_layers)
        active_index = max(me.uv_layers.active_index, 0) if uv_layers else 0
    else:
        active = me.uv_layers.active
        uv_layers = [active] if active is not None else []
        active_index = 0
    uv_info = {
        "names": [layer.name for layer in uv_layers],
        "active_index": active_index,
        "active_render": next(
            (k for k, layer in enumerate(uv_layers) if layer.active_render), 0),
    }
    color_layer = me.color_attributes.active_color if me.color_attributes else None
    color_per_loop = color_layer is not None and color_layer.domain == 'CORNER'
    color_per_point = color_layer is not None and color_layer.domain == 'POINT'

    # Every color attribute layer is carried through per-vertex (guidance-style,
    # like importance: not in the dedup key, not in the error metric - zero
    # effect on simplification quality). CORNER layers collapse to one value
    # per dedup vertex, so per-corner color seams are not preserved by design.
    color_layers = list(me.color_attributes) if me.color_attributes else []
    color_info = {
        "names": [layer.name for layer in color_layers],
        "types": [layer.data_type for layer in color_layers],
        "active_index": max(me.color_attributes.active_color_index, 0) if color_layers else 0,
        "render_index": max(me.color_attributes.render_color_index, 0) if color_layers else 0,
    }

    # Every buffer is pulled out of Blender whole (foreach_get) and the dedup
    # runs as a sort, not as a Python loop over corners: at a few million
    # triangles the per-corner RNA access alone costs tens of seconds.
    n_corners = len(me.loop_triangles) * 3
    n_loops = len(me.loops)

    corner_vert = np.empty(n_corners, dtype=np.int32)
    me.loop_triangles.foreach_get("vertices", corner_vert)
    corner_loop = np.empty(n_corners, dtype=np.int32)
    me.loop_triangles.foreach_get("loops", corner_loop)
    tri_poly = np.empty(len(me.loop_triangles), dtype=np.int32)
    me.loop_triangles.foreach_get("polygon_index", tri_poly)

    poly_mat = np.zeros(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("material_index", poly_mat)
    corner_mat = np.repeat(poly_mat[tri_poly], 3)

    co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)

    loop_normal = np.empty(n_loops * 3, dtype=np.float32)
    me.corner_normals.foreach_get("vector", loop_normal)
    corner_normal = loop_normal.reshape(-1, 3)[corner_loop]

    if uv_layers:
        layer_uvs = []
        for layer in uv_layers:
            flat = np.empty(n_loops * 2, dtype=np.float32)
            layer.uv.foreach_get("vector", flat)
            layer_uvs.append(flat.reshape(-1, 2)[corner_loop])
        corner_uv = np.concatenate(layer_uvs, axis=1)
        uv_cols = corner_uv.shape[1]
    else:
        corner_uv = np.zeros((n_corners, 2), dtype=np.float32)
        uv_cols = 0

    # The dedup key as integers - values quantized to 1e-5, the same tolerance
    # the previous tuple key rounded to. Columns are vertex index, corner
    # normal, every captured UV, material id. key_normals=False drops the
    # normal columns for a flat-shaded source (see source_is_flat_shaded).
    key = np.empty((n_corners, 2 + uv_cols + (3 if key_normals else 0)), dtype=np.int64)
    key[:, 0] = corner_vert
    col = 1
    if key_normals:
        key[:, col:col + 3] = np.rint(corner_normal.astype(np.float64) * 1e5)
        col += 3
    if uv_cols:
        key[:, col:col + uv_cols] = np.rint(corner_uv.astype(np.float64) * 1e5)
    key[:, -1] = corner_mat

    # lexsort reads its keys last-to-first, so the reversed view makes column
    # 0 the primary one; equal keys then sit next to each other.
    order = np.lexsort(key.T[::-1])
    sorted_key = key[order]
    new_group = np.ones(n_corners, dtype=bool)
    np.any(sorted_key[1:] != sorted_key[:-1], axis=1, out=new_group[1:])
    indices = np.empty(n_corners, dtype=np.int64)
    indices[order] = np.cumsum(new_group) - 1
    first = order[new_group]

    # Renumber from sort order back to first-encounter order, so the buffers
    # come out in the same order the loop triangles reference them.
    appearance = np.argsort(first, kind='stable')
    rank = np.empty_like(appearance)
    rank[appearance] = np.arange(len(appearance))
    indices = rank[indices].astype(np.uint32)
    first = first[appearance]

    first_vert = corner_vert[first]
    first_loop = corner_loop[first]

    if vgroup_weights is not None:
        importance = vgroup_weights[first_vert]
    elif color_per_loop or color_per_point:
        src = first_loop if color_per_loop else first_vert
        importance = _lum(_read_color_layer(color_layer)[src])
    else:
        importance = np.zeros(len(first), dtype=np.float32)

    if color_layers:
        colors = np.concatenate(
            [_read_color_layer(layer)[first_loop if layer.domain == 'CORNER' else first_vert]
             for layer in color_layers], axis=1)
    else:
        colors = np.zeros((len(first), 0), dtype=np.float32)

    return (
        co[first_vert],
        corner_normal[first],
        corner_uv[first],
        indices,
        uv_info,
        corner_mat[first].astype(np.int32),
        importance.astype(np.float32, copy=False),
        vgroup_weights is not None or color_layer is not None,
        colors.astype(np.float32, copy=False),
        color_info,
    )


def compact_after_simplify(positions, simplified_indices, normals=None, uvs=None, mat_ids=None,
                            colors=None, importance=None):
    unique_idx, inverse = np.unique(simplified_indices, return_inverse=True)
    new_positions = positions[unique_idx]
    new_faces = inverse.astype(np.uint32).reshape(-1, 3)
    new_normals = normals[unique_idx] if normals is not None else None
    new_uvs = uvs[unique_idx] if uvs is not None else None
    new_mat_ids = mat_ids[unique_idx] if mat_ids is not None else None
    new_colors = colors[unique_idx] if colors is not None else None
    new_importance = importance[unique_idx] if importance is not None else None
    return (new_positions, new_faces, new_normals, new_uvs, new_mat_ids,
            new_colors, new_importance)


MESHOPT_LOCK_BORDER = 1      # meshopt_SimplifyLockBorder
MESHOPT_SPARSE = 2           # meshopt_SimplifySparse
MESHOPT_ERROR_ABSOLUTE = 4   # meshopt_SimplifyErrorAbsolute
MESHOPT_PRUNE = 8            # meshopt_SimplifyPrune


def apply_sparse_option(options, positions, indices):
    """meshopt_SimplifySparse states a precondition, not a preference: it is
    valid exactly when the index buffer references only part of the vertex
    buffer (it also makes target_error relative to that subset's extents).
    That is a property of the buffers we just built - after the pre-prune
    pass, or with loose vertices - so it's decided here instead of being a
    checkbox users have no way to evaluate. Any incoming bit is cleared so a
    stale preset can't force it on a dense buffer."""
    options &= ~MESHOPT_SPARSE
    if len(indices):
        used = np.zeros(positions.shape[0], dtype=bool)
        used[indices] = True
        if int(used.sum()) < positions.shape[0]:
            options |= MESHOPT_SPARSE
    return options


def as_c_float_p(np_array):
    arr = np.ascontiguousarray(np_array, dtype=np.float32)
    return arr.ctypes.data_as(c_float_p), arr


def as_c_uint_p(np_array):
    arr = np.ascontiguousarray(np_array, dtype=np.uint32)
    return arr.ctypes.data_as(c_uint_p), arr


def native_simplify_prune(positions, indices, prune_threshold):
    """meshopt_simplifyPrune: standalone pre-pass that removes small
    disconnected components whose size (relative to mesh extents) is below
    prune_threshold, without doing any other simplification. Unlike the
    MESHOPT_PRUNE option flag (whose threshold is tied to Target Error),
    this gives an independent knob - e.g. aggressively strip debris at 0.1
    while keeping the main simplification precise at a low Target Error."""
    lib = native_build._native_lib

    destination = np.zeros_like(indices)
    dest_ptr, destination = as_c_uint_p(destination)
    idx_ptr, indices = as_c_uint_p(indices)
    pos_ptr, positions = as_c_float_p(positions)

    count = lib.meshopt_simplifyPrune(
        dest_ptr, idx_ptr, len(indices),
        pos_ptr, positions.shape[0], positions.shape[1] * 4,
        float(prune_threshold),
    )
    return destination[:count]


def native_simplify_positions(positions, indices, target_index_count, target_error, options):
    lib = native_build._native_lib

    destination = np.zeros_like(indices)
    dest_ptr, destination = as_c_uint_p(destination)
    idx_ptr, indices = as_c_uint_p(indices)
    pos_ptr, positions = as_c_float_p(positions)

    result_error = ctypes.c_float(0.0)
    count = lib.meshopt_simplify(
        dest_ptr, idx_ptr, len(indices),
        pos_ptr, positions.shape[0], positions.shape[1] * 4,
        int(target_index_count), float(target_error), options, ctypes.byref(result_error),
    )
    return destination[:count], result_error.value


def _position_groups(positions, scale=1e5):
    """Group vertices by position quantized to 1/scale, without a Python dict of
    rounded tuples: at tens of millions of vertices that loop alone runs for
    minutes. Returns the sort order, the group-start mask over it, and each
    sorted element's group representative. lexsort is stable, so the
    representative is the group's lowest original index - what iterating in
    index order used to pick."""
    q = np.rint(np.asarray(positions, dtype=np.float64) * scale).astype(np.int64)
    order = np.lexsort((q[:, 2], q[:, 1], q[:, 0]))
    sorted_q = q[order]
    starts = np.ones(len(order), dtype=bool)
    if len(order) > 1:
        np.any(sorted_q[1:] != sorted_q[:-1], axis=1, out=starts[1:])
    group = np.cumsum(starts) - 1
    return order, starts, group, order[starts][group]


def build_seam_protect_lock(positions, uvs, has_uv, mat_ids=None):
    """Equivalent to meshopt_generatePositionRemap + comparing attributes per
    the docs' 'protect specific seams' recipe - group vertices by position,
    flag any vertex whose UV or material ID differs from another vertex
    sharing its position. Used with Permissive so the simplifier can collapse
    freely everywhere except across the seams/material boundaries we
    explicitly protect.

    A vertex alone at its position can never differ from the group's
    representative, so single-vertex groups drop out on their own - no need to
    filter them the way the per-group loop this replaces did."""
    lock = np.zeros(len(positions), dtype=np.uint8)
    if len(positions) == 0:
        return lock
    order, _, _, rep = _position_groups(positions)
    differs = np.zeros(len(order), dtype=bool)
    if has_uv:
        # np.allclose's tolerances, matching the per-vertex call this replaces
        same = np.isclose(uvs[order], uvs[rep], rtol=1e-5, atol=1e-5)
        np.logical_or(differs, ~np.all(same, axis=1), out=differs)
    if mat_ids is not None:
        np.logical_or(differs, mat_ids[order] != mat_ids[rep], out=differs)
    lock[order[differs]] |= native_build.MESHOPT_VERTEX_PROTECT
    lock[rep[differs]] |= native_build.MESHOPT_VERTEX_PROTECT
    return lock


def _build_attr_array(normals, uvs, has_uv, normal_weight, uv_weight,
                       importance=None, importance_weight=0.0):
    """Assemble the interleaved attribute array + matching per-attribute
    weights that meshoptimizer expects. Optionally appends a vertex-color
    importance column: higher color (weighted) = costlier to collapse."""
    cols = [normals * normal_weight]
    if has_uv:
        cols.append(uvs * uv_weight)
    if importance is not None and importance_weight > 0.0:
        cols.append((importance * importance_weight).reshape(-1, 1))
    attrs = np.concatenate(cols, axis=1).astype(np.float32)
    weights = np.ones(attrs.shape[1], dtype=np.float32)
    return np.ascontiguousarray(attrs), weights


def native_simplify_attributes(positions, normals, uvs, has_uv, indices,
                                target_index_count, target_error, options,
                                normal_weight, uv_weight, vertex_lock=None,
                                importance=None, importance_weight=0.0):
    lib = native_build._native_lib

    attrs, weights = _build_attr_array(
        normals, uvs, has_uv, normal_weight, uv_weight, importance, importance_weight)

    destination = np.zeros_like(indices)
    dest_ptr, destination = as_c_uint_p(destination)
    idx_ptr, indices = as_c_uint_p(indices)
    pos_ptr, positions = as_c_float_p(positions)
    attr_ptr, attrs = as_c_float_p(attrs)
    weight_ptr, weights = as_c_float_p(weights)

    if vertex_lock is not None:
        lock_arr = np.ascontiguousarray(vertex_lock, dtype=np.uint8)
        lock_ptr = lock_arr.ctypes.data_as(c_ubyte_p)
    else:
        lock_arr = None
        lock_ptr = None

    result_error = ctypes.c_float(0.0)
    count = lib.meshopt_simplifyWithAttributes(
        dest_ptr, idx_ptr, len(indices),
        pos_ptr, positions.shape[0], positions.shape[1] * 4,
        attr_ptr, attrs.shape[1] * 4,
        weight_ptr, attrs.shape[1],
        lock_ptr,
        int(target_index_count), float(target_error), options, ctypes.byref(result_error),
    )
    return destination[:count], result_error.value


def native_simplify_with_update(positions, normals, uvs, has_uv, indices,
                                 target_index_count, target_error, options,
                                 normal_weight, uv_weight, vertex_lock=None,
                                 importance=None, importance_weight=0.0):
    """meshopt_simplifyWithUpdate actually moves vertex positions and
    attributes to better-fitting locations for the new topology (rather than
    only choosing among the original vertices), which reduces UV/shape
    distortion at very aggressive simplification ratios. It mutates
    indices/vertex_positions/vertex_attributes IN PLACE, so we work on our
    own private copies and rebuild a clean, compacted mesh afterward."""
    attrs, weights = _build_attr_array(
        normals, uvs, has_uv, normal_weight, uv_weight, importance, importance_weight)

    positions = np.ascontiguousarray(positions, dtype=np.float32).copy()
    indices = np.ascontiguousarray(indices, dtype=np.uint32).copy()
    attrs = np.ascontiguousarray(attrs, dtype=np.float32)

    idx_ptr = indices.ctypes.data_as(c_uint_p)
    pos_ptr = positions.ctypes.data_as(c_float_p)
    attr_ptr = attrs.ctypes.data_as(c_float_p)
    weight_ptr, weights = as_c_float_p(weights)

    if vertex_lock is not None:
        lock_arr = np.ascontiguousarray(vertex_lock, dtype=np.uint8)
        lock_ptr = lock_arr.ctypes.data_as(c_ubyte_p)
    else:
        lock_arr = None
        lock_ptr = None

    result_error = ctypes.c_float(0.0)
    count = native_build._native_lib.meshopt_simplifyWithUpdate(
        idx_ptr, len(indices),
        pos_ptr, positions.shape[0], positions.shape[1] * 4,
        attr_ptr, attrs.shape[1] * 4,
        weight_ptr, attrs.shape[1],
        lock_ptr,
        int(target_index_count), float(target_error), options, ctypes.byref(result_error),
    )

    new_indices = indices[:count]

    # attrs holds weighted values; divide back out to recover true units.
    # (The trailing importance column, if any, is ignored on the way out.)
    new_normals = attrs[:, :3] / normal_weight if normal_weight else attrs[:, :3]
    # simplifyWithUpdate blends attribute values, so normals come back
    # non-unit-length; the meshoptimizer README requires renormalizing
    # ("Attributes that have specific constraints like normals ... should
    # be renormalized or clamped after the function returns new data").
    lengths = np.linalg.norm(new_normals, axis=1, keepdims=True)
    np.divide(new_normals, lengths, out=new_normals, where=lengths > 1e-12)
    if has_uv:
        uv_cols = uvs.shape[1]
        new_uvs = attrs[:, 3:3 + uv_cols] / uv_weight if uv_weight else attrs[:, 3:3 + uv_cols]
    else:
        new_uvs = None

    return positions, new_indices, new_normals, new_uvs, result_error.value


def mesh_tri_count(me):
    """Triangle count of a mesh (n-gons counted as len-2 tris), via foreach_get
    so it stays cheap even on dense meshes."""
    n = len(me.polygons)
    if n == 0:
        return 0
    loop_totals = np.empty(n, dtype=np.int32)
    me.polygons.foreach_get("loop_total", loop_totals)
    return int(np.maximum(loop_totals - 2, 0).sum())


def _select_only(obj):
    """Make obj the sole selected + active object in OBJECT mode - required
    before running a modifier operator on it."""
    view_layer = bpy.context.view_layer
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in view_layer.objects:
        o.select_set(o == obj)
    view_layer.objects.active = obj


def build_decimate_importance_group(obj, importance, lock_threshold=None):
    """Feed our importance map to Blender's Decimate as a vertex group.
    Semantics come straight from bmesh_decimate_collapse.cc:

        if (vweights && (w1 == 0.0f || w2 == 0.0f)) goto clear;   // never collapse
        e_weight = 2.0f - (w1 + w2);
        cost += edge_length * (e_weight * vweight_factor);

    so LOW weight = expensive = preserved, and weight exactly 0 is a hard
    lock - the inverse of our 'white = important' convention. We therefore
    store (1 - importance), and only let it reach a true 0 when the user
    asked for a hard lock; otherwise a pure-white area would silently
    become uncollapsible and stall the finish pass."""
    weights = 1.0 - np.clip(np.asarray(importance, dtype=np.float32), 0.0, 1.0)
    if lock_threshold is not None:
        weights = np.where(importance >= lock_threshold, 0.0, np.maximum(weights, 1e-3))
    else:
        weights = np.maximum(weights, 1e-3)

    group = obj.vertex_groups.new(name=DECIMATE_IMPORTANCE_GROUP)
    zero_idx = np.flatnonzero(weights <= 0.0)
    if zero_idx.size:
        group.add(zero_idx.tolist(), 0.0, 'REPLACE')
    # Quantized buckets: one add() call per distinct weight instead of one per
    # vertex - the Python call overhead dominates on dense meshes, and 1/64
    # resolution is far finer than this cost term needs.
    rest = np.flatnonzero(weights > 0.0)
    if rest.size:
        buckets = np.clip(np.rint(weights[rest] * 64.0).astype(np.int32), 1, 64)
        for b in np.unique(buckets):
            group.add(rest[buckets == b].tolist(), float(b) / 64.0, 'REPLACE')
    return group


def decimate_to_target(obj, target_tris, vertex_group=None, vertex_group_factor=1.0):
    """Finishing pass with Blender's own Decimate (Collapse) for the case
    where meshoptimizer stops well above the requested triangle count.

    Attribute-aware simplification treats UV/normal/material seams as hard
    boundaries and gets stuck; the meshopt ways around that (Permissive)
    collapse ACROSS those seams, which snaps UVs to one side of the seam and
    smears the texture. Blender's Decimate interpolates UVs along the
    collapsed edge instead, so pushing the last stretch with it keeps the
    texture readable at very low polycounts.

    Runs after Merge by Distance on purpose: the welded mesh stores UVs per
    face-corner, which is what lets Decimate interpolate them. Returns the
    resulting triangle count."""
    me = obj.data
    current = mesh_tri_count(me)
    if target_tris < 1 or current <= target_tris:
        return current

    _select_only(obj)
    mod = obj.modifiers.new("SF_DecimateFinish", 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = target_tris / current
    mod.use_collapse_triangulate = True
    if vertex_group is not None:
        mod.vertex_group = vertex_group
        # Blender clamps this at 1000; our 0-1 strength maps so that the 0.5
        # default lands on Blender's own default factor of 1.0.
        mod.vertex_group_factor = min(1000.0, max(0.0, vertex_group_factor) * 2.0)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return mesh_tri_count(obj.data)


# Above this many distinct positions in one search cell the threshold is
# comparable to the mesh's own detail, enumerating pairs turns quadratic, and
# the job goes to merge_by_distance instead.
_WELD_MAX_CELL = 64


class WeldTooDense(Exception):
    pass


def _distance_pairs(pos, threshold):
    """Index pairs closer than threshold, via 8 grids of cell size 2*threshold
    shifted half a cell in each combination of axes. Per axis two close
    coordinates share a cell in at least one of the two offsets, so nothing is
    missed; a single grid misses any pair straddling a cell edge."""
    cell_size = 2.0 * threshold
    scaled = np.asarray(pos, dtype=np.float64) / cell_size
    found = []
    for offset in np.ndindex(2, 2, 2):
        cell = np.floor(scaled + np.array(offset) * 0.5).astype(np.int64)
        # Cell coordinates hashed into one key: sorting one column is much
        # cheaper than lexsort over three, and that sort is the whole cost
        # here. A collision only costs time - the distance test drops the pair.
        key = ((cell[:, 0].astype(np.uint64) * np.uint64(73856093))
               ^ (cell[:, 1].astype(np.uint64) * np.uint64(19349663))
               ^ (cell[:, 2].astype(np.uint64) * np.uint64(83492791)))
        order = np.argsort(key, kind='stable')
        sorted_key = key[order]
        starts = np.ones(len(order), dtype=bool)
        if len(order) > 1:
            np.not_equal(sorted_key[1:], sorted_key[:-1], out=starts[1:])
        sizes = np.diff(np.append(np.flatnonzero(starts), len(order)))
        biggest = int(sizes.max(initial=0))
        if biggest > _WELD_MAX_CELL:
            raise WeldTooDense(f"{biggest} positions within {threshold} of each other")
        if biggest < 2:
            continue
        # Single-point cells pair with nothing and are nearly all of them;
        # dropping them keeps the strides below off the full vertex count.
        group = np.cumsum(starts) - 1
        crowded = np.repeat(sizes > 1, sizes)
        sub_order, sub_group = order[crowded], group[crowded]
        # Every pair inside a cell, as (element, element d places later in the
        # same cell) for each stride - no Python loop over the cells.
        for stride in range(1, biggest):
            same = sub_group[:-stride] == sub_group[stride:]
            if not same.any():
                continue
            a, b = sub_order[:-stride][same], sub_order[stride:][same]
            close = np.linalg.norm(pos[a] - pos[b], axis=1) <= threshold
            if close.any():
                found.append(np.stack([a[close], b[close]], axis=1))
    if not found:
        return np.zeros((0, 2), dtype=np.int64)
    # A pair the offsets found more than once can come back either way round.
    return np.unique(np.sort(np.concatenate(found), axis=1), axis=0)


def _union_labels(labels, pairs):
    """Merge the label of each pair, then renumber the survivors from 0. The
    loop runs over pairs, which are few; resolving the chains afterwards is
    pointer jumping over the whole label array, since a Python find() per label
    is minutes on a dense mesh."""
    parent = np.arange(int(labels.max()) + 1, dtype=np.int64)

    def root(x):
        while parent[x] != x:
            x = parent[x]
        return x

    for a, b in pairs:
        ra, rb = root(labels[a]), root(labels[b])
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    # A parent always points at a smaller label, so this settles in a few
    # passes however the pairs chained together.
    while True:
        nxt = parent[parent]
        if np.array_equal(nxt, parent):
            break
        parent = nxt
    _, renumbered = np.unique(parent, return_inverse=True)
    return renumbered[labels]


def weld_position_buffers(positions, faces, threshold):
    """Merge by Distance on the buffers, before the mesh is built. One vertex
    survives per group of positions within the threshold; corner_attr keeps the
    corner->vertex map, so UVs, normals and material IDs stay per corner and
    nothing is averaged. Degenerate triangles are dropped, duplicate faces are
    not. Returns (positions, faces, corner_attr, rep) or None when nothing is
    coincident; rep maps each survivor back to its original vertex."""
    faces = np.asarray(faces)
    if len(positions) == 0 or len(faces) == 0:
        return None
    order, starts, group, _ = _position_groups(positions, scale=1e9)
    rep = order[starts]
    labels = np.empty(len(positions), dtype=np.int64)
    labels[order] = group

    if threshold > 0.0 and len(rep) > 1:
        pairs = _distance_pairs(positions[rep], float(threshold))
        if len(pairs):
            labels = _union_labels(labels, rep[pairs])
            # Survivor per group is again its lowest index, and the labels come
            # back renumbered, so first-occurrence order is the new numbering.
            _, rep = np.unique(labels, return_index=True)

    if len(rep) == len(positions):
        return None
    welded = labels[faces].astype(np.uint32)
    keep = ((welded[:, 0] != welded[:, 1]) & (welded[:, 1] != welded[:, 2])
            & (welded[:, 0] != welded[:, 2]))
    return (positions[rep], welded[keep],
            faces[keep].ravel().astype(np.uint32), rep)


# Recalculate + Smooth is a single checkbox in Light, so its two knobs are
# constants rather than settings - the values Pro's presets ship with. Crease is
# in radians: edges meeting sharper than this stay hard.
SMOOTH_CREASE_ANGLE = math.radians(45.0)
SMOOTH_RELAX = 1.5


def generate_normals(obj, crease_angle=SMOOTH_CREASE_ANGLE, smoothing=SMOOTH_RELAX):
    """Per-corner normals from meshoptimizer as custom split normals; False
    when the bundled library lacks the export. Edges above crease_angle stay
    hard; smoothing is a Laplacian relaxation weighted by normal alignment, so
    creases survive it. This replaces the source normals rather than adding to
    them, which is the point on a very aggressive LOD - the source ones no
    longer match the geometry that is left."""
    fn = native_build.generate_normals_fn()
    if fn is None:
        return False
    me = obj.data
    me.calc_loop_triangles()
    tri_count = len(me.loop_triangles)
    vert_count = len(me.vertices)
    if tri_count == 0 or vert_count == 0:
        return False

    indices = np.empty(tri_count * 3, dtype=np.uint32)
    me.loop_triangles.foreach_get("vertices", indices)
    loops = np.empty(tri_count * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("loops", loops)
    positions = np.empty(vert_count * 3, dtype=np.float32)
    me.vertices.foreach_get("co", positions)

    result = np.empty(tri_count * 3 * 3, dtype=np.float32)
    fn(result.ctypes.data_as(c_float_p),
       indices.ctypes.data_as(c_uint_p), tri_count * 3,
       positions.ctypes.data_as(c_float_p), vert_count, 12,
       ctypes.c_float(crease_angle), ctypes.c_float(smoothing))

    # One normal per triangle corner comes back; Blender wants one per loop.
    # loop_triangles carries the mapping, so this holds for ngons too.
    loop_normals = np.zeros((len(me.loops), 3), dtype=np.float32)
    loop_normals[loops] = result.reshape(-1, 3)
    # A flat-shaded face ignores custom normals, so make sure none are left.
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), dtype=np.int32))
    me.normals_split_custom_set(loop_normals.tolist())
    return True


def merge_by_distance(obj, threshold):
    """Weld coincident-position vertices back together. Safe for UV seams:
    Blender stores UV/normals per face-corner (loop), not per vertex, so
    merging vertices that happen to share a position does not blend or lose
    their distinct per-loop UV/normal data - it only welds the topology
    (removes duplicate-position vertices, connects edges properly). Keep the
    threshold small so it only welds truly-coincident points (seams, or
    float-precision duplicates) rather than nearby-but-intentionally-separate
    geometry."""
    view_layer = bpy.context.view_layer
    for o in view_layer.objects:
        o.select_set(o == obj)
    view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=threshold)
    bpy.ops.object.mode_set(mode='OBJECT')


def deselect_mesh_elements(me):
    """A freshly built LOD arrives selected, so Edit Mode would open on it
    that way. Runs last, after the mesh is final.

    Done by dropping the .select_* attributes, which is where the selection
    lives: absent means nothing is selected, and Blender rebuilds them on
    demand. The obvious vertices/edges/polygons.foreach_set("select", ...)
    instead reads a bool array as ints and can fault on a dense mesh.

    The attributes are matched while iterating, never looked up by name:
    attributes.get(".select_edge") reports the data type of a different
    attribute in Blender 5.0, and acting on that would be a mistake."""
    doomed = [attr for attr in me.attributes
              if attr.name in {".select_vert", ".select_edge", ".select_poly"}]
    for attr in doomed:
        me.attributes.remove(attr)


def build_object_from_buffers(name, collections, positions, faces, normals=None, uvs=None,
                               materials=None, mat_ids=None, uv_info=None,
                               colors=None, color_info=None, corner_attr=None):
    mesh = bpy.data.meshes.new(name)
    # Filled through foreach_set rather than from_pydata: the latter needs the
    # buffers as Python lists, which on a multi-million-triangle LOD costs more
    # than everything else here put together. Triangles only, so the polygon
    # offsets are a fixed stride of 3.
    n_loops = len(faces) * 3
    mesh.vertices.add(len(positions))
    mesh.loops.add(n_loops)
    mesh.polygons.add(len(faces))
    mesh.vertices.foreach_set("co", np.ascontiguousarray(positions, dtype=np.float32).ravel())
    mesh.loops.foreach_set("vertex_index", np.ascontiguousarray(faces, dtype=np.int32).ravel())
    mesh.polygons.foreach_set("loop_start", np.arange(0, n_loops, 3, dtype=np.int32))
    # Smooth exactly when custom split normals follow: they are packed against
    # each corner's computed normal, and on a flat face that base differs per
    # corner - such a LOD reads back split at nearly every corner.
    mesh.polygons.foreach_set(
        "use_smooth", np.full(len(faces), normals is not None, dtype=np.int32))
    mesh.update(calc_edges=True)

    # Corner -> attribute row, for writing the per-corner layers below.
    corner_vert = np.ascontiguousarray(
        faces if corner_attr is None else corner_attr, dtype=np.int64).ravel()

    if uvs is not None:
        # uvs is (N, 2*num_layers); uv_info carries the source layers' names
        # and active/active_render flags so the LOD matches the original.
        names = uv_info["names"] if uv_info and uv_info["names"] else ["UVMap"]
        num_layers = uvs.shape[1] // 2
        for k in range(num_layers):
            layer_name = names[k] if k < len(names) else f"UVMap.{k:03d}"
            uv_layer = mesh.uv_layers.new(name=layer_name)
            flat = np.ascontiguousarray(uvs[corner_vert, 2 * k:2 * k + 2], dtype=np.float32)
            uv_layer.uv.foreach_set("vector", flat.ravel())
        if uv_info:
            render_idx = uv_info["active_render"]
            if 0 <= render_idx < len(mesh.uv_layers):
                mesh.uv_layers[render_idx].active_render = True
            active_idx = uv_info["active_index"]
            if 0 <= active_idx < len(mesh.uv_layers):
                mesh.uv_layers.active_index = active_idx

    if colors is not None and color_info and color_info["names"]:
        # colors is (N, 4*num_layers). Always written as POINT domain:
        # per-vertex is all the pipeline carries (see mesh_to_attribute_buffers).
        for k, (cname, ctype) in enumerate(zip(color_info["names"], color_info["types"])):
            attr = mesh.color_attributes.new(name=cname, type=ctype, domain='POINT')
            flat = np.ascontiguousarray(colors[:, 4 * k:4 * k + 4], dtype=np.float32).ravel()
            attr.data.foreach_set("color", flat)
        render_idx = color_info["render_index"]
        if 0 <= render_idx < len(mesh.color_attributes):
            mesh.color_attributes.render_color_index = render_idx
        active_idx = color_info["active_index"]
        if 0 <= active_idx < len(mesh.color_attributes):
            mesh.color_attributes.active_color_index = active_idx

    if normals is not None:
        try:
            if corner_attr is not None:
                # Welded vertices carry several normals, so per corner, and
                # against final topology. The array goes in as itself:
                # .tolist() here costs gigabytes of small Python lists.
                mesh.normals_split_custom_set(
                    np.ascontiguousarray(normals, dtype=np.float32)[corner_vert])
            elif hasattr(mesh, "normals_split_custom_set_from_vertices"):
                mesh.normals_split_custom_set_from_vertices(
                    np.ascontiguousarray(normals, dtype=np.float32).tolist())
        except Exception:
            # Blender rejects custom normals on degenerate results (zero-area
            # or unreferenced verts after an aggressive collapse). The mesh is
            # still valid - it just keeps face normals.
            pass

    if materials:
        for mat in materials:
            mesh.materials.append(mat)

    if mat_ids is not None and len(mesh.materials) > 1:
        # All 3 corners of a surviving triangle share the same material ID by
        # construction (mesh_to_attribute_buffers bakes it into the vertex
        # dedup key), so the first vertex's ID is authoritative.
        per_face = np.asarray(mat_ids, dtype=np.int32)[corner_vert.reshape(-1, 3)[:, 0]]
        mesh.polygons.foreach_set(
            "material_index", np.clip(per_face, 0, len(mesh.materials) - 1))

    obj = bpy.data.objects.new(name, mesh)
    for collection in collections:
        collection.objects.link(obj)
    return obj



def simplify_object(context, src, ratio, target_error, options, use_attributes,
                     normal_weight, uv_weight, name, do_merge, merge_threshold,
                     use_vertex_update=False, protect_uv_seams=False,
                     use_vcolor_importance=False, importance_weight=0.5,
                     preprune_threshold=0.0, use_multi_uv=False,
                     use_decimate_finish=False, importance_source='VCOLOR',
                     importance_vgroup="", use_smooth_normals=False,
                     smooth_crease_angle=SMOOTH_CREASE_ANGLE):
    eval_obj, me = get_evaluated_mesh(context, src)
    new_mat_ids = None
    new_colors = None
    uv_info = None
    color_info = None
    try:
        # Materials must come from the evaluated object/mesh - the same data
        # mat_ids are read from. src.data.materials misses materials that are
        # linked to the OBJECT (material slots, e.g. on Alt+D instances) or
        # that appear only after evaluation (geometry nodes instancing).
        # MaterialSlot.material resolves the Object-vs-Data link itself;
        # None entries are kept so material_index values stay aligned. The
        # evaluated object hands out evaluated copies of the datablocks -
        # take .original, a persistent mesh must not reference evaluated IDs.
        slots = eval_obj.material_slots
        materials = []
        for slot_i in range(max(len(me.materials), len(slots))):
            mat = None
            if slot_i < len(slots) and slots[slot_i].material is not None:
                mat = slots[slot_i].material
            elif slot_i < len(me.materials):
                mat = me.materials[slot_i]
            materials.append(mat.original if mat is not None else None)
        # The group is picked by name, never guessed, so on a rigged mesh the
        # bone weight groups are simply left alone.
        vgroup_weights = None
        if use_attributes and use_vcolor_importance and importance_source == 'VGROUP':
            vgroup_weights = read_vertex_group_weights(eval_obj, me, importance_vgroup)
            if vgroup_weights is None:
                print(f"[LOD Generator] Importance vertex group "
                      f"'{importance_vgroup}' not found on {src.name} - "
                      f"simplifying without an importance mask.")
        # Flat faces plus custom normals is what an FBX/OBJ import usually
        # produces, and the dedup key cannot survive it - see the function.
        if use_attributes and repack_flat_custom_normals(me):
            print(f"[LOD Generator] {src.name} is flat-shaded and carries custom "
                  f"split normals - re-packing them on the working copy so the "
                  f"vertex dedup can merge (the source itself is not touched)")

        # A fully flat source carries no normal information the geometry does
        # not already have, so it neither enters the dedup key nor comes back
        # out as custom split normals - the LOD stays flat, like the source.
        flat_source = use_attributes and source_is_flat_shaded(me)
        if use_attributes:
            (positions, normals, uvs, indices, uv_info, mat_ids,
             importance, has_color, colors, color_info) = mesh_to_attribute_buffers(
                me, use_multi_uv, vgroup_weights, key_normals=not flat_source)
            has_uv = bool(uv_info["names"])
            colors_arg = colors if color_info["names"] else None
            target_index_count = max(3, int(len(indices) * ratio))
            target_index_count -= target_index_count % 3

            imp_arg = importance if (use_vcolor_importance and has_color) else None
            imp_w = importance_weight if (use_vcolor_importance and has_color) else 0.0

            vertex_lock = None
            if protect_uv_seams and (options & native_build.MESHOPT_PERMISSIVE):
                vertex_lock = build_seam_protect_lock(positions, uvs, has_uv, mat_ids)

            if preprune_threshold > 0.0:
                indices = native_simplify_prune(positions, indices, preprune_threshold)
            options = apply_sparse_option(options, positions, indices)

            if use_vertex_update:
                upd_pos, simplified, upd_norm, upd_uv, result_error = native_simplify_with_update(
                    positions, normals, uvs, has_uv, indices,
                    target_index_count, target_error, options,
                    normal_weight, uv_weight, vertex_lock=vertex_lock,
                    importance=imp_arg, importance_weight=imp_w,
                )
                (new_pos, new_faces, new_norm, new_uv, new_mat_ids, new_colors,
                 new_importance) = compact_after_simplify(
                    upd_pos, simplified, upd_norm, upd_uv if has_uv else None, mat_ids,
                    colors_arg, imp_arg)
            else:
                simplified, result_error = native_simplify_attributes(
                    positions, normals, uvs, has_uv, indices,
                    target_index_count, target_error, options,
                    normal_weight, uv_weight, vertex_lock=vertex_lock,
                    importance=imp_arg, importance_weight=imp_w,
                )
                (new_pos, new_faces, new_norm, new_uv, new_mat_ids, new_colors,
                 new_importance) = compact_after_simplify(
                    positions, simplified, normals, uvs if has_uv else None, mat_ids,
                    colors_arg, imp_arg)
        else:
            positions, indices = mesh_to_position_buffers(me)
            target_index_count = max(3, int(len(indices) * ratio))
            target_index_count -= target_index_count % 3
            if preprune_threshold > 0.0:
                indices = native_simplify_prune(positions, indices, preprune_threshold)
            options = apply_sparse_option(options, positions, indices)
            simplified, result_error = native_simplify_positions(
                positions, indices, target_index_count, target_error, options)
            (new_pos, new_faces, new_norm, new_uv, new_mat_ids, new_colors,
             new_importance) = compact_after_simplify(positions, simplified)
    finally:
        eval_obj.to_mesh_clear()

    # On the buffers, not on the built object: the mesh is born welded, so the
    # custom normals below are written against topology that no longer moves.
    # merge_on_object is the fallback for the one case the buffer weld
    # declines - geometry too dense for its threshold.
    corner_attr = None
    merge_on_object = False
    if do_merge and new_faces.shape[0]:
        try:
            welded = weld_position_buffers(new_pos, new_faces, merge_threshold)
        except Exception as exc:
            print(f"[LOD Generator] Buffer weld gave up on {name} ({exc}) - "
                  f"welding with the Edit Mode operator instead")
            welded, merge_on_object = None, True
        if welded is not None:
            new_pos, new_faces, corner_attr, weld_rep = welded
            if new_colors is not None:
                new_colors = new_colors[weld_rep]
            if new_importance is not None:
                new_importance = new_importance[weld_rep]

    before_tris = len(indices) // 3
    after_tris = new_faces.shape[0]

    # Nothing left: adding an object with no triangles used to happen silently.
    # Checked on the result, not on the settings - if it isn't zero, nothing
    # about the behavior changes.
    if new_faces.shape[0] == 0:
        if len(indices) < 3:
            raise SimplifyEmpty(f"{name}: the source mesh has no triangles")
        raise SimplifyEmpty(
            f"{name}: simplification returned 0 triangles. Lower Target Error "
            f"(Prune removes whole disconnected parts once the error budget "
            f"covers them) or use a mode without Prune")

    # The LOD lands in the source object's own collection(s), not the active
    # one, so the scene hierarchy of the family matches the original.
    collections = list(src.users_collection) or [context.collection]
    obj = build_object_from_buffers(
        name, collections, new_pos, new_faces,
        # A flat source gets no custom split normals back (see flat_source):
        # the LOD stays flat, exactly like the mesh it came from. Under
        # Recalculate + Smooth the source normals are replaced wholesale after
        # the topology is final, so carrying them here would be wasted work.
        new_norm if not (flat_source or use_smooth_normals) else None, new_uv,
        materials=materials if any(m is not None for m in materials) else None,
        mat_ids=new_mat_ids, uv_info=uv_info,
        colors=new_colors, color_info=color_info,
        corner_attr=corner_attr,
    )
    # Mirror the source's place in the hierarchy: same parent (if any),
    # same world transform either way.
    if src.parent is not None:
        obj.parent = src.parent
        obj.parent_type = src.parent_type
        if src.parent_type == 'BONE':
            obj.parent_bone = src.parent_bone
        obj.matrix_parent_inverse = src.matrix_parent_inverse.copy()
    obj.matrix_world = src.matrix_world.copy()

    # Built before Merge by Distance so the weights are indexed by the same
    # vertices we just wrote; welding merges the weights along with the
    # vertices, so the group stays valid for the Decimate pass afterwards.
    # Kept as a NAME, not as the VertexGroup pointer: applying the Decimate
    # modifier below rebuilds the object's data and leaves such a pointer
    # dangling, so reading .name off it afterwards returns a truncated string
    # and removing it raises "DeformGroup '<garbage>' not in object".
    importance_group_name = None
    if use_decimate_finish and new_importance is not None:
        try:
            importance_group_name = build_decimate_importance_group(
                obj, new_importance).name
        except Exception as exc:
            print(f"[LOD Generator] Importance group for Decimate failed on "
                  f"{obj.name}: {exc}")

    if merge_on_object:
        try:
            merge_by_distance(obj, merge_threshold)
        except Exception as exc:
            print(f"[LOD Generator] Merge by Distance failed on {obj.name}: {exc}")

    # After the weld: the mesh keeps per-corner UVs, which is what lets Decimate
    # interpolate them instead of snapping across seams.
    if use_decimate_finish:
        try:
            after_tris = decimate_to_target(
                obj, target_index_count // 3,
                vertex_group=importance_group_name,
                vertex_group_factor=importance_weight)
        except Exception as exc:
            print(f"[LOD Generator] Decimate finish failed on {obj.name}: {exc}")
        if importance_group_name:
            # Internal artifact (it holds inverted importance) - don't leave it
            # on the finished LOD. Looked up again by name, and inside the try:
            # losing the cleanup must not lose the whole LOD.
            try:
                stale = obj.vertex_groups.get(importance_group_name)
                if stale is not None:
                    obj.vertex_groups.remove(stale)
            except Exception as exc:
                print(f"[LOD Generator] Could not remove the temporary "
                      f"importance group on {obj.name}: {exc}")

    # After the Decimate finish, so the generator sees the topology that is
    # actually left - recalculating before it would describe a mesh that no
    # longer exists.
    if use_smooth_normals and not generate_normals(obj, smooth_crease_angle):
        print(f"[LOD Generator] meshoptimizer in this build cannot generate "
              f"normals - {obj.name} keeps the normals it was built with")

    # Last, once the mesh is final: Merge by Distance selects everything to do
    # its work, so clearing the selection any earlier would be undone.
    deselect_mesh_elements(obj.data)

    return obj, before_tris, after_tris, result_error
