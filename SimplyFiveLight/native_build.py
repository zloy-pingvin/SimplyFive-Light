"""Load the bundled meshoptimizer native library via ctypes.

A pre-built plain shared library (lodgen_meshopt*.dll / .so / .dylib) ships
right next to this file, together with meshopt_flags.json recording the real
enum values for that build. mesh_ops.py and __init__.py only ever read state
from this module (e.g. native_build.MESHOPT_PERMISSIVE) - never copy the
mutable globals by value, since try_load_native() reassigns them after import.

This Light build only loads the bundled library; it does not download or
compile meshoptimizer from source.
"""

import os
import sys
import json
import ctypes


def get_dll_ext():
    return ".dll" if sys.platform.startswith("win") else (".dylib" if sys.platform == "darwin" else ".so")


_native_lib = None
MESHOPT_PERMISSIVE = 16      # meshopt_SimplifyPermissive; overwritten from flags below
MESHOPT_VERTEX_PROTECT = 1   # meshopt_SimplifyVertex_Protect; overwritten from flags below

c_float_p = ctypes.POINTER(ctypes.c_float)
c_uint_p = ctypes.POINTER(ctypes.c_uint)
c_ubyte_p = ctypes.POINTER(ctypes.c_ubyte)


def _configure_signatures(lib):
    lib.meshopt_simplify.restype = ctypes.c_size_t
    lib.meshopt_simplify.argtypes = [
        c_uint_p, c_uint_p, ctypes.c_size_t, c_float_p, ctypes.c_size_t, ctypes.c_size_t,
        ctypes.c_size_t, ctypes.c_float, ctypes.c_uint, c_float_p,
    ]
    lib.meshopt_simplifyWithAttributes.restype = ctypes.c_size_t
    lib.meshopt_simplifyWithAttributes.argtypes = [
        c_uint_p, c_uint_p, ctypes.c_size_t, c_float_p, ctypes.c_size_t, ctypes.c_size_t,
        c_float_p, ctypes.c_size_t, c_float_p, ctypes.c_size_t, c_ubyte_p,
        ctypes.c_size_t, ctypes.c_float, ctypes.c_uint, c_float_p,
    ]
    lib.meshopt_simplifyWithUpdate.restype = ctypes.c_size_t
    lib.meshopt_simplifyWithUpdate.argtypes = [
        c_uint_p, ctypes.c_size_t, c_float_p, ctypes.c_size_t, ctypes.c_size_t,
        c_float_p, ctypes.c_size_t, c_float_p, ctypes.c_size_t, c_ubyte_p,
        ctypes.c_size_t, ctypes.c_float, ctypes.c_uint, c_float_p,
    ]
    # size_t meshopt_simplifyPrune(unsigned int* destination, const unsigned int* indices,
    #     size_t index_count, const float* vertex_positions, size_t vertex_count,
    #     size_t vertex_positions_stride, float target_error);
    lib.meshopt_simplifyPrune.restype = ctypes.c_size_t
    lib.meshopt_simplifyPrune.argtypes = [
        c_uint_p, c_uint_p, ctypes.c_size_t, c_float_p, ctypes.c_size_t, ctypes.c_size_t,
        ctypes.c_float,
    ]


def _bundled_dll_path():
    """The .dll/.so/.dylib placed right next to this .py file. Matches by glob
    rather than an exact name, since a build's output can carry a timestamp
    (lodgen_meshopt_<N>.dll); a plain "lodgen_meshopt.dll" copy works too."""
    import glob
    script_dir = os.path.dirname(os.path.abspath(__file__))
    exact = os.path.join(script_dir, "lodgen_meshopt" + get_dll_ext())
    if os.path.exists(exact):
        return exact
    matches = sorted(glob.glob(os.path.join(script_dir, "lodgen_meshopt*" + get_dll_ext())))
    return matches[0] if matches else None


def native_available():
    return _native_lib is not None


def try_load_native():
    """Load the bundled shared library via ctypes (stdlib only, no extra pip
    package needed) and read its meshopt_flags.json for the real enum values."""
    global _native_lib, MESHOPT_PERMISSIVE, MESHOPT_VERTEX_PROTECT

    dll_path = _bundled_dll_path()
    if not dll_path:
        return False

    try:
        lib = ctypes.CDLL(dll_path)
        _configure_signatures(lib)
        _native_lib = lib

        flags_path = os.path.join(os.path.dirname(dll_path), "meshopt_flags.json")
        if os.path.exists(flags_path):
            try:
                with open(flags_path, "r", encoding="utf-8") as handle:
                    flags = json.load(handle)
                MESHOPT_PERMISSIVE = int(flags.get("permissive", MESHOPT_PERMISSIVE))
                MESHOPT_VERTEX_PROTECT = int(flags.get("protect", MESHOPT_VERTEX_PROTECT))
            except Exception as exc:
                print(f"[LOD Generator] Could not read flags file, using defaults: {exc}")
        else:
            print("[LOD Generator] WARNING: meshopt_flags.json not found next to the "
                  "bundled library - Permissive/Protect are using guessed fallback "
                  "values, which may be wrong for this build.")
        return True
    except Exception as exc:
        print(f"[LOD Generator] Could not load bundled native library: {exc}")
        return False
