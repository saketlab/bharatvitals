import json
from typing import Literal, Optional

from mcp.types import ToolAnnotations

READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=True)


def to_json(data: object) -> str:
    # indentation costs the model tokens
    return json.dumps(data, separators=(",", ":"))


# allowed values appear in the schema the model sees
Sector = Optional[Literal["total", "rural", "urban"]]
Match = Literal["fixed", "regex", "fuzzy"]

__all__ = ["READ_ONLY", "Match", "Sector", "to_json"]
