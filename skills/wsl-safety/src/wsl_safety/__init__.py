"""WSL Filesystem Safety - __init__.py"""

from wsl_safety._impl import (
    safe_search,
    copy_from_windows,
    install_patches,
    _safe_glob,
    _safe_iglob,
    _safe_walk,
)

# Patches are auto-installed when _impl is imported
__version__ = "1.0.0"
__all__ = ["safe_search", "copy_from_windows", "install_patches"]
