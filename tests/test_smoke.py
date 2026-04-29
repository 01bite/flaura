import importlib

import pytest


def test_import_assert():
    try:
        importlib.import_module("flaura")
    except ImportError:
        pytest.fail("module flaura not found")
