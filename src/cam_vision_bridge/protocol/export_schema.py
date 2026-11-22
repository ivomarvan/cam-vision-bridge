"""Write the committed JSON Schema for protocol v1 text messages.

Run from a checkout of this repository:

    python -m cam_vision_bridge.protocol.export_schema
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from cam_vision_bridge.protocol.messages import TextMessage

# Pydantic 2 emits draft 2020-12 for these models. The dialect is written on the
# file so a reader does not have to infer it.
_JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
_SCHEMA_TITLE = "CamVisionBridgeV1TextMessage"
_SCHEMA_DESCRIPTION = (
    "Protocol v1 JSON messages. Field t selects the message and v is 1. "
    "Result items are a second t-discriminated union inside result.items."
)
SCHEMA_FILE_NAME = "cam-vision-bridge-v1.schema.json"


def export_schema(path: Path) -> None:
    """Write the JSON Schema of the v1 text-message union.

    Args:
        path: Destination file. Parent directories are created. An existing
            file is overwritten.

    Returns:
        None.

    Raises:
        OSError: If the directory or file cannot be written.
    """
    generated = TypeAdapter(TextMessage).json_schema()
    document: dict[str, Any] = {
        "$schema": _JSON_SCHEMA_DIALECT,
        "title": _SCHEMA_TITLE,
        "description": _SCHEMA_DESCRIPTION,
    }
    document.update(generated)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def default_schema_path() -> Path:
    """Return the committed schema path inside this repository checkout.

    The directory is the nearest parent of this module that contains
    ``pyproject.toml``, not the process cwd. Library code does not call
    ``git_root_to_syspath``.

    Returns:
        Absolute path of ``schema/cam-vision-bridge-v1.schema.json``.

    Raises:
        FileNotFoundError: If no parent directory contains ``pyproject.toml``.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return parent / "schema" / SCHEMA_FILE_NAME
    raise FileNotFoundError("pyproject.toml not found above the protocol package")


def main() -> None:
    """Write the schema to the default repository path.

    Returns:
        None.

    Raises:
        FileNotFoundError: If the repository root cannot be located.
        OSError: If the schema file cannot be written.
    """
    export_schema(default_schema_path())


if __name__ == "__main__":
    main()
