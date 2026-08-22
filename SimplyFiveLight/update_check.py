# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 zloy_pingvin
"""Optional version check against a small JSON on the product site.

The request runs on a worker thread that touches nothing but urllib, and the
answer is handed back through bpy.app.timers - the only place bpy is safe to
call. Nothing here can block or fail a generation: every error path ends in a
silent None, and the add-on works exactly the same offline.

Two sources, tried in order. Preferred is a small document next to the site's
index, all fields optional except "version":

    {"version": "1.4.0",
     "url": "https://zloy-pingvin.github.io/SimplyFive-Light/index.html",
     "notes": "what changed"}

If it is not there the landing page itself is read, which already carries the
number in its "Current version" row. That keeps the check working with nothing
added to the site, at the cost of breaking silently if the page is redesigned -
hence the json first.
"""

import json
import re
import threading
import urllib.request

import bpy

SITE = "https://zloy-pingvin.github.io/SimplyFive-Light/"
VERSION_URL = SITE + "version.json"
PAGE_URL = SITE + "index.html"
TIMEOUT = 5.0
CHECK_INTERVAL_DAYS = 1

_running = False
_cancelled = False

_VERSION_RE = re.compile(r'^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?')
# The landing page's "Current version" row: <span class="ver-now">... <b>v1.3.5</b>
_PAGE_RE = re.compile(r'ver-now.{0,300}?<b[^>]*>\s*v?(\d+\.\d+(?:\.\d+)?)\s*</b>',
                      re.S | re.I)


def parse_version(text):
    """(1, 4, 0) from "1.4.0", "v1.4" or "1.4.0-beta"; None if unparseable."""
    if not isinstance(text, str):
        return None
    m = _VERSION_RE.match(text)
    if not m:
        return None
    return tuple(int(g) if g else 0 for g in m.groups())


def is_newer(latest, current):
    a, b = parse_version(latest), tuple(current)
    return a is not None and a > b


def _read(url, limit):
    """Capped read: a mistyped or hijacked URL can point at anything."""
    req = urllib.request.Request(url, headers={"User-Agent": "SimplyFive"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return response.read(limit).decode("utf-8", "replace")


def _fetch(url, page_url):
    try:
        return json.loads(_read(url, 64 * 1024))
    except Exception as exc:
        first = exc
    if not page_url:
        raise first
    match = _PAGE_RE.search(_read(page_url, 512 * 1024))
    if not match:
        raise first
    return {"version": match.group(1), "url": page_url}


def _worker(url, callback, page_url):
    global _running
    try:
        data = _fetch(url, page_url)
    except Exception as exc:
        print(f"[LOD Generator] update check failed: {exc}")
        data = None

    def deliver():
        global _running
        _running = False
        if not _cancelled:
            try:
                callback(data)
            except Exception as exc:
                print(f"[LOD Generator] update check callback failed: {exc}")
        return None

    bpy.app.timers.register(deliver, first_interval=0.0)


def start(url, callback, page_url=PAGE_URL):
    """Returns False if a check is already in flight."""
    global _running, _cancelled
    if _running:
        return False
    _running = True
    _cancelled = False
    threading.Thread(target=_worker, args=(url, callback, page_url),
                     daemon=True).start()
    return True


def cancel():
    """Unregister must not leave a callback pointing at a dead class."""
    global _cancelled
    _cancelled = True
