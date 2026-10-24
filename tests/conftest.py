import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from zsc.paths import RAW_HISTORY  # noqa: E402


@pytest.fixture(scope="session")
def snapshot():
    from zsc.pipeline import load_snapshot
    return load_snapshot()


@pytest.fixture(scope="session")
def history():
    from zsc.data import load_history
    return load_history(RAW_HISTORY, first_season=1995)
