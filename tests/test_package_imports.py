"""Smoke tests for installable package layout and import paths."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.unit
def test_import_root_package() -> None:
    import cam_vision_bridge

    assert cam_vision_bridge.__name__ == "cam_vision_bridge"


@pytest.mark.unit
def test_import_subpackages() -> None:
    import cam_vision_bridge.api
    import cam_vision_bridge.core
    import cam_vision_bridge.protocol
    import cam_vision_bridge.transport

    assert cam_vision_bridge.api.__name__ == "cam_vision_bridge.api"
    assert cam_vision_bridge.core.__name__ == "cam_vision_bridge.core"
    assert cam_vision_bridge.protocol.__name__ == "cam_vision_bridge.protocol"
    assert cam_vision_bridge.transport.__name__ == "cam_vision_bridge.transport"


@pytest.mark.unit
def test_version_is_nonempty_string() -> None:
    import cam_vision_bridge

    assert isinstance(cam_vision_bridge.__version__, str)
    assert len(cam_vision_bridge.__version__) > 0


@pytest.mark.unit
def test_missing_submodule_raises_module_not_found() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("cam_vision_bridge.missing")
