"""Process-level resource containment for pipeline commands."""

from __future__ import annotations

import os

DEFAULT_MAX_MEMORY_MB = 2048
_THREAD_ENV_VARS = (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)


def configure_process(max_memory_mb: int) -> None:
    """Bound memory and numerical-library threads before heavy imports.

    ``RLIMIT_AS`` converts accidental unbounded allocation into a local
    ``MemoryError`` rather than allowing the operating system to reclaim the
    desktop. It is available on Linux and most Unix-like systems; platforms
    without it still receive the thread limits.
    """
    if max_memory_mb < 256:
        raise ValueError("--max-memory-mb must be at least 256")

    threads = os.environ.get("GLOTTOGENERA_NUM_THREADS", "1")
    for name in _THREAD_ENV_VARS:
        os.environ[name] = threads

    try:
        import resource
    except ImportError:  # pragma: no cover - Windows fallback
        return

    if not hasattr(resource, "RLIMIT_AS"):  # pragma: no cover - platform fallback
        return
    requested = max_memory_mb * 1024 * 1024
    current_soft, current_hard = resource.getrlimit(resource.RLIMIT_AS)
    if current_soft != resource.RLIM_INFINITY:
        requested = min(requested, current_soft)
    if current_hard != resource.RLIM_INFINITY:
        requested = min(requested, current_hard)
    resource.setrlimit(resource.RLIMIT_AS, (requested, current_hard))
