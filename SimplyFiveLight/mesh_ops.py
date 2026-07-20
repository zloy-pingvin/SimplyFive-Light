"""Mesh <-> numpy buffers, and the actual calls into the compiled
meshoptimizer library (native_build._native_lib). Reads native_build's
mutable state through the module (native_build.X), never via 'from
native_build import X', since that would freeze in whatever value X had at
import time - before try_load_native() has actually set it.
"""

import bpy
import ctypes
import numpy as np

from . import native_build
from .native_build import c_float_p, c_uint_p, c_ubyte_p


def get_evaluated_mesh(context, obj):
    depsgraph = context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    me = eval_obj.to_mesh()
    return eval_obj, me


def boundary_vertex_mask(me):
    edge_face_count = {}
    for poly in me.polygons:
        verts = poly.vertices
        n = len(verts)
        for i in range(n):
            a, b = verts[i], verts[(i + 1) % n]
            key = (a, b) if a < b else (b, a)
            edge_face_count[key] = edge_face_count.get(key, 0) + 1
    mask = np.zeros(len(me.vertices), dtype=np.uint8)
    for (a, b), c in edge_face_count.items():
        if c == 1:
            mask[a] = 1
            mask[b] = 1
    return mask


def mesh_to_position_buffers(me):
    me.calc_loop_triangles()
    positions = np.empty((len(me.vertices), 3), dtype=np.float32)
    me.vertices.foreach_get("co", positions.ravel())
    tris = me.loop_triangles
    flat = np.empty(len(tris) * 3, dtype=np.int32)
    tris.foreach_get("vertices", flat)
    indices = flat.astype(np.uint32)
    return positions, indices


def mesh_to_attribute_buffers(me, use_multi_uv=False):
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

    Also captures a per-vertex 'importance' scalar (0-1) from the active
    color attribute, if present: luminance of the vertex color. Higher =
    more important = should be simplified less. Not part of the dedup key
    (it's guidance, not topology).

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
    uv_data = [layer.data for layer in uv_layers]
    verts = me.vertices
    loops = me.loops
    polygons = me.polygons

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

    def _lum(rgba):
        return 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]

    lookup = {}
    positions, normals, uvs, mat_ids, importance, colors = [], [], [], [], [], []
    indices = np.empty(len(me.loop_triangles) * 3, dtype=np.uint32)

    idx_out = 0
    for tri in me.loop_triangles:
        mat_id = polygons[tri.polygon_index].material_index
        for vi, li in zip(tri.vertices, tri.loops):
            n = loops[li].normal
            if uv_data:
                uv = []
                for data in uv_data:
                    lu, lv = data[li].uv
                    uv.append(lu)
                    uv.append(lv)
                key = (vi, round(n[0], 5), round(n[1], 5), round(n[2], 5),
                       *(round(c, 5) for c in uv), mat_id)
            else:
                uv = (0.0, 0.0)
                key = (vi, round(n[0], 5), round(n[1], 5), round(n[2], 5), mat_id)

            if color_per_loop:
                imp = _lum(color_layer.data[li].color)
            elif color_per_point:
                imp = _lum(color_layer.data[vi].color)
            else:
                imp = 0.0

            new_i = lookup.get(key)
            if new_i is None:
                new_i = len(positions)
                lookup[key] = new_i
                positions.append(tuple(verts[vi].co))
                normals.append((n[0], n[1], n[2]))
                uvs.append(tuple(uv))
                mat_ids.append(mat_id)
                importance.append(imp)
                col_vals = []
                for layer in color_layers:
                    elem = layer.data[li] if layer.domain == 'CORNER' else layer.data[vi]
                    col_vals.extend(elem.color)
                colors.append(tuple(col_vals))
            indices[idx_out] = new_i
            idx_out += 1

    return (
        np.array(positions, dtype=np.float32),
        np.array(normals, dtype=np.float32),
        np.array(uvs, dtype=np.float32),
        indices,
        uv_info,
        np.array(mat_ids, dtype=np.int32),
        np.array(importance, dtype=np.float32),
        color_layer is not None,
        np.array(colors, dtype=np.float32),
        color_info,
    )


def compact_after_simplify(positions, simplified_indices, normals=None, uvs=None, mat_ids=None,
                            colors=None):
    unique_idx, inverse = np.unique(simplified_indices, return_inverse=True)
    new_positions = positions[unique_idx]
    new_faces = inverse.astype(np.uint32).reshape(-1, 3)
    new_normals = normals[unique_idx] if normals is not None else None
    new_uvs = uvs[unique_idx] if uvs is not None else None
    new_mat_ids = mat_ids[unique_idx] if mat_ids is not None else None
    new_colors = colors[unique_idx] if colors is not None else None
    return new_positions, new_faces, new_normals, new_uvs, new_mat_ids, new_colors


MESHOPT_LOCK_BORDER = 1      # meshopt_SimplifyLockBorder
MESHOPT_SPARSE = 2           # meshopt_SimplifySparse
MESHOPT_ERROR_ABSOLUTE = 4   # meshopt_SimplifyErrorAbsolute
MESHOPT_PRUNE = 8            # meshopt_SimplifyPrune


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


def build_seam_protect_lock(positions, uvs, has_uv, mat_ids=None):
    """Equivalent to meshopt_generatePositionRemap + comparing attributes per
    the docs' 'protect specific seams' recipe - group vertices by position,
    flag any vertex whose UV or material ID differs from another vertex
    sharing its position. Used with Permissive so the simplifier can collapse
    freely everywhere except across the seams/material boundaries we
    explicitly protect."""
    groups = {}
    for i, p in enumerate(positions):
        key = (round(float(p[0]), 5), round(float(p[1]), 5), round(float(p[2]), 5))
        groups.setdefault(key, []).append(i)

    lock = np.zeros(len(positions), dtype=np.uint8)
    for idxs in groups.values():
        if len(idxs) < 2:
            continue
        base_uv = uvs[idxs[0]] if has_uv else None
        base_mat = mat_ids[idxs[0]] if mat_ids is not None else None
        for i in idxs:
            differs = False
            if has_uv and not np.allclose(uvs[i], base_uv, atol=1e-5):
                differs = True
            if mat_ids is not None and mat_ids[i] != base_mat:
                differs = True
            if differs:
                lock[idxs[0]] |= native_build.MESHOPT_VERTEX_PROTECT
                lock[i] |= native_build.MESHOPT_VERTEX_PROTECT
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


def build_object_from_buffers(name, collections, positions, faces, normals=None, uvs=None,
                               materials=None, mat_ids=None, uv_info=None,
                               colors=None, color_info=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(positions.tolist(), [], faces.tolist())
    mesh.update(calc_edges=True)

    if uvs is not None:
        # uvs is (N, 2*num_layers); uv_info carries the source layers' names
        # and active/active_render flags so the LOD matches the original.
        names = uv_info["names"] if uv_info and uv_info["names"] else ["UVMap"]
        num_layers = uvs.shape[1] // 2
        for k in range(num_layers):
            layer_name = names[k] if k < len(names) else f"UVMap.{k:03d}"
            uv_layer = mesh.uv_layers.new(name=layer_name)
            for loop in mesh.loops:
                u, v = uvs[loop.vertex_index, 2 * k:2 * k + 2]
                uv_layer.data[loop.index].uv = (float(u), float(v))
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

    if normals is not None and hasattr(mesh, "normals_split_custom_set_from_vertices"):
        try:
            mesh.normals_split_custom_set_from_vertices([tuple(n) for n in normals.tolist()])
        except Exception:
            pass

    if materials:
        for mat in materials:
            mesh.materials.append(mat)

    if mat_ids is not None and len(mesh.materials) > 1:
        max_index = len(mesh.materials) - 1
        for poly in mesh.polygons:
            # All 3 corners of a surviving triangle share the same material
            # ID by construction (mesh_to_attribute_buffers bakes it into the
            # vertex dedup key), so the first vertex's ID is authoritative.
            mid = int(mat_ids[poly.vertices[0]])
            poly.material_index = max(0, min(mid, max_index))

    obj = bpy.data.objects.new(name, mesh)
    for collection in collections:
        collection.objects.link(obj)
    return obj



def simplify_object(context, src, ratio, target_error, options, use_attributes,
                     normal_weight, uv_weight, name, do_merge, merge_threshold,
                     use_vertex_update=False, protect_uv_seams=False,
                     use_vcolor_importance=False, importance_weight=0.5,
                     preprune_threshold=0.0, use_multi_uv=False):
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
        if use_attributes:
            (positions, normals, uvs, indices, uv_info, mat_ids,
             importance, has_color, colors, color_info) = mesh_to_attribute_buffers(me, use_multi_uv)
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

            if use_vertex_update:
                upd_pos, simplified, upd_norm, upd_uv, result_error = native_simplify_with_update(
                    positions, normals, uvs, has_uv, indices,
                    target_index_count, target_error, options,
                    normal_weight, uv_weight, vertex_lock=vertex_lock,
                    importance=imp_arg, importance_weight=imp_w,
                )
                new_pos, new_faces, new_norm, new_uv, new_mat_ids, new_colors = compact_after_simplify(
                    upd_pos, simplified, upd_norm, upd_uv if has_uv else None, mat_ids, colors_arg)
            else:
                simplified, result_error = native_simplify_attributes(
                    positions, normals, uvs, has_uv, indices,
                    target_index_count, target_error, options,
                    normal_weight, uv_weight, vertex_lock=vertex_lock,
                    importance=imp_arg, importance_weight=imp_w,
                )
                new_pos, new_faces, new_norm, new_uv, new_mat_ids, new_colors = compact_after_simplify(
                    positions, simplified, normals, uvs if has_uv else None, mat_ids, colors_arg)
        else:
            positions, indices = mesh_to_position_buffers(me)
            target_index_count = max(3, int(len(indices) * ratio))
            target_index_count -= target_index_count % 3
            if preprune_threshold > 0.0:
                indices = native_simplify_prune(positions, indices, preprune_threshold)
            simplified, result_error = native_simplify_positions(
                positions, indices, target_index_count, target_error, options)
            new_pos, new_faces, new_norm, new_uv, new_mat_ids, new_colors = compact_after_simplify(positions, simplified)
    finally:
        eval_obj.to_mesh_clear()

    before_tris = len(indices) // 3
    after_tris = new_faces.shape[0]

    # The LOD lands in the source object's own collection(s), not the active
    # one, so the scene hierarchy of the family matches the original.
    collections = list(src.users_collection) or [context.collection]
    obj = build_object_from_buffers(
        name, collections, new_pos, new_faces,
        new_norm, new_uv,
        materials=materials if any(m is not None for m in materials) else None,
        mat_ids=new_mat_ids, uv_info=uv_info,
        colors=new_colors, color_info=color_info,
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

    if do_merge:
        try:
            merge_by_distance(obj, merge_threshold)
        except Exception as exc:
            print(f"[LOD Generator] Merge by Distance failed on {obj.name}: {exc}")

    return obj, before_tris, after_tris, result_error


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------
