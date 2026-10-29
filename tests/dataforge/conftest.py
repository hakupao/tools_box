import gc

import pytest


@pytest.fixture(autouse=True)
def _collect_garbage_on_main_thread():
    """Collect Qt-owning garbage on the main thread so no worker thread ever triggers it."""
    yield
    gc.collect()
