import gc

import pytest


@pytest.fixture(scope="session", autouse=True)
def _disable_automatic_gc_for_session():
    """Mirror the app: no automatic GC (it could run on a worker thread and destroy Qt garbage)."""
    was_enabled = gc.isenabled()
    gc.disable()
    yield
    if was_enabled:
        gc.enable()


@pytest.fixture(autouse=True)
def _collect_garbage_on_main_thread():
    """Collect Qt-owning garbage on the main thread so no worker thread ever triggers it."""
    yield
    gc.collect()
