"""The committed JSON Schema matches a fresh export of the v1 models."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import cam_vision_bridge.protocol.export_schema as export_schema_module
from cam_vision_bridge.protocol.export_schema import export_schema

pytestmark = pytest.mark.unit

_MESSAGE_TAGS = {"hello", "welcome", "error", "frame", "result"}
_RESULT_TAGS = {"box", "quad", "polygon", "keypoints", "polyline", "text", "metrics"}


def test_committed_schema_matches_regenerated_schema(tmp_path: Path) -> None:
    committed = export_schema_module.default_schema_path()
    generated = tmp_path / "cam-vision-bridge-v1.schema.json"
    export_schema(generated)
    assert generated.read_text(encoding="utf-8") == committed.read_text(encoding="utf-8")


def test_export_schema_lists_message_and_result_tags(tmp_path: Path) -> None:
    destination = tmp_path / "nested" / "schema.json"
    export_schema(destination)
    schema = json.loads(destination.read_text(encoding="utf-8"))
    assert set(schema["discriminator"]["mapping"]) == _MESSAGE_TAGS
    item_schema = schema["$defs"]["Result"]["properties"]["items"]["items"]
    assert set(item_schema["discriminator"]["mapping"]) == _RESULT_TAGS
    assert schema["$defs"]["Hello"]["additionalProperties"] is False


def test_main_writes_schema_at_default_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "cam-vision-bridge-v1.schema.json"
    monkeypatch.setattr(export_schema_module, "default_schema_path", lambda: target)
    export_schema_module.main()
    assert target.is_file()
    assert target.read_text(encoding="utf-8").endswith("\n")
