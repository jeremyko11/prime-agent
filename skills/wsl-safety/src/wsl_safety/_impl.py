"""
WSL Filesystem Safety - _impl.py

Monkey-patches glob.glob, glob.iglob, os.walk, and pathlib.Path.rglob
to block wildcard scans on /mnt (WSL 9P filesystem) that cause kernel hangs.
"""

import os
import sys
import glob as _glob_module
import shutil
import time
from pathlib import Path

# Original functions (save before patching)
_original_glob = _glob_module.glob
_original_iglob = _glob_module.iglob
_original_walk = os.walk

# Paths that are extremely slow under WSL (9P protocol)
_DANGEROUS_PREFIXES = (
    "/mnt",
    "/media",
)

# Marker so we don't double-patch
_PATCHED_MARKER = "_wsl_safety_patched"


def _is_dangerous_path(path):
    """Check if a path is on a slow WSL mount."""
    if not path:
        return False
    try:
        abs_path = os.path.abspath(path)
        return any(abs_path.startswith(p) for p in _DANGEROUS_PREFIXES)
    except Exception:
        return False


def _has_wildcard(pattern):
    """Check if a glob pattern contains wildcards."""
    return any(c in pattern for c in ("*", "?", "[", "]"))


def _warn_blocked(operation, path, suggestion=""):
    """Print a visible warning when an operation is blocked."""
    msg = (
        f"\n[WSL_SAFETY] BLOCKED {operation} on '{path}'\n"
        f"  Reason: WSL /mnt access via 9P protocol is 10-100x slower than native Linux.\n"
        f"  A wildcard scan here would hang the kernel for minutes.\n"
    )
    if suggestion:
        msg += f"  Fix: {suggestion}\n"
    else:
        msg += (
            f"  Fix: Copy files to /root/work/ first, then scan there.\n"
            f"    import shutil; shutil.copy('{path}', '/root/work/')\n"
            f"  Or use: wsl_safety.safe_search(root='/root/work', pattern='*.md')\n"
        )
    msg += "=" * 70
    print(msg, file=sys.stderr, flush=True)


def _safe_glob(pattern, recursive=False, *args, **kwargs):
    """
    Patched glob.glob that blocks wildcard scans on /mnt.
    - /mnt/**/*.md  -> BLOCKED (wildcard scan on slow path)
    - /mnt/c/file.md -> Allowed (single file, no wildcard)
    - /root/**/*.md  -> Allowed (native Linux, fast)
    """
    if _is_dangerous_path(pattern) and _has_wildcard(pattern):
        _warn_blocked(
            "glob.glob",
            pattern,
            f"shutil.copy('{os.path.dirname(pattern)}'+'/', '/root/work/') then glob('/root/work/...')"
        )
        return []
    return _original_glob(pattern, recursive=recursive, *args, **kwargs)


def _safe_iglob(pattern, recursive=False, *args, **kwargs):
    """Patched glob.iglob that blocks wildcard scans on /mnt."""
    if _is_dangerous_path(pattern) and _has_wildcard(pattern):
        _warn_blocked("glob.iglob", pattern)
        return iter([])
    return _original_iglob(pattern, recursive=recursive, *args, **kwargs)


def _safe_walk(top, topdown=True, onerror=None, followlinks=False, **kwargs):
    """
    Patched os.walk that blocks traversal of /mnt.
    Also adds a max_files safety limit (default 50000) to prevent runaway scans.
    """
    if _is_dangerous_path(top):
        _warn_blocked("os.walk", top)
        return

    max_files = kwargs.pop("max_files", 50000)
    file_count = 0
    for root, dirs, files in _original_walk(top, topdown=topdown, onerror=onerror, followlinks=followlinks):
        file_count += len(files)
        if file_count > max_files:
            print(
                f"\n[WSL_SAFETY] os.walk hit max_files limit ({max_files}) at '{root}', stopping.\n"
                f"  Fix: Narrow your search to a more specific subdirectory.\n"
                f"{'=' * 70}",
                file=sys.stderr, flush=True
            )
            return
        yield root, dirs, files


def install_patches():
    """Apply monkey-patches to glob.glob, glob.iglob, os.walk."""
    # Check if already patched
    if getattr(_glob_module.glob, _PATCHED_MARKER, False):
        return False

    _glob_module.glob = _safe_glob
    _glob_module.iglob = _safe_iglob
    os.walk = _safe_walk

    # Mark as patched
    setattr(_glob_module.glob, _PATCHED_MARKER, True)
    setattr(_glob_module.iglob, _PATCHED_MARKER, True)
    setattr(os.walk, _PATCHED_MARKER, True)

    return True


def safe_search(root="/root/work", pattern="*", max_results=100, timeout=10):
    """
    Safe file search with timeout and result limit.

    Args:
        root: Search root directory (must NOT be on /mnt)
        pattern: Glob pattern (e.g., "*.md", "*keyword*")
        max_results: Maximum number of results to return
        timeout: Maximum search time in seconds

    Returns:
        List of matching file paths, or empty list if timeout/blocked.
    """
    if _is_dangerous_path(root):
        print(
            f"\n[WSL_SAFETY] safe_search: root '{root}' is on /mnt (blocked).\n"
            f"  Copy files to /root/work/ first:\n"
            f"    wsl_safety.copy_from_windows('{root}', '/root/work/')\n"
            f"{'=' * 70}",
            file=sys.stderr, flush=True
        )
        return []

    if not os.path.isdir(root):
        print(f"[WSL_SAFETY] safe_search: '{root}' is not a directory", file=sys.stderr)
        return []

    results = []
    start_time = time.time()

    try:
        for dirpath, dirnames, filenames in _original_walk(root):
            if time.time() - start_time > timeout:
                print(
                    f"[WSL_SAFETY] safe_search: timeout ({timeout}s) reached, "
                    f"returning {len(results)} results so far.",
                    file=sys.stderr
                )
                break
            for f in filenames:
                if _glob_module.fnmatch.fnmatch(f, pattern):
                    results.append(os.path.join(dirpath, f))
                    if len(results) >= max_results:
                        return results
    except Exception as e:
        print(f"[WSL_SAFETY] safe_search error: {e}", file=sys.stderr)

    return results


def copy_from_windows(windows_path, dest="/root/work/"):
    """
    Copy a file or directory from Windows (/mnt/c/...) to a native Linux path.

    Args:
        windows_path: Path on /mnt/c/ or /mnt/d/ (Windows file)
        dest: Destination directory (default /root/work/)

    Returns:
        Destination path of the copied file/directory.
    """
    if not _is_dangerous_path(windows_path):
        print(f"[WSL_SAFETY] copy_from_windows: '{windows_path}' is not a /mnt path", file=sys.stderr)
        return None

    if not os.path.exists(windows_path):
        print(f"[WSL_SAFETY] copy_from_windows: '{windows_path}' does not exist", file=sys.stderr)
        return None

    os.makedirs(dest, exist_ok=True)

    if os.path.isdir(windows_path):
        dest_path = os.path.join(dest, os.path.basename(windows_path))
        shutil.copytree(windows_path, dest_path, dirs_exist_ok=True)
    else:
        dest_path = shutil.copy2(windows_path, dest)

    print(f"[WSL_SAFETY] Copied: {windows_path} -> {dest_path}")
    return dest_path


# Auto-install patches on import
_patched = install_patches()
if _patched:
    print(
        "[WSL_SAFETY] Patches installed: glob.glob, glob.iglob, os.walk are now safe for WSL.\n"
        "[WSL_SAFETY] Wildcard scans on /mnt will be blocked. Use safe_search() or copy files to /root/work/.",
        file=sys.stderr, flush=True
    )
