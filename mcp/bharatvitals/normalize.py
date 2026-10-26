"""Repair the argument mistakes LLMs make before FastMCP validates a tool call."""

import json
import re
from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

from bharatvitals.tools._common import to_json

# wrong names models use, by the parameter they mean
SYNONYMS = {
    "states": "state",
    "region": "state",
    "state_name": "state",
    "years": "year",
    "indicators": "indicator",
    "districts": "district",
    "gender": "sex",
    "sexes": "sex",
    "sectors": "sector",
    "start_date": "from_date",
    "start": "from_date",
    "from": "from_date",
    "start_month": "from_date",
    "end_date": "to_date",
    "end": "to_date",
    "to": "to_date",
    "end_month": "to_date",
    "page_size": "limit",
    "max_rows": "limit",
    "rows": "limit",
    "skip": "offset",
    "causes": "cause",
    "tables": "table",
    "periods": "period",
}

# values meaning "no filter"; dropped for optional parameters
NO_FILTER = {
    "",
    "all",
    "any",
    "*",
    "none",
    "null",
    "nil",
    "n/a",
    "na",
    "everything",
    "every",
}

# spellings the R APIs do not resolve; keys lowercase, spaces collapsed
STATE_ALIASES = {
    "delhi nct": "Delhi",
    "nct delhi": "Delhi",
    "nct of delhi": "Delhi",
    "new delhi": "Delhi",
    "j&k": "Jammu & Kashmir",
    "j & k": "Jammu & Kashmir",
    "j and k": "Jammu & Kashmir",
    "jammu kashmir": "Jammu & Kashmir",
    "a&n": "Andaman & Nicobar Islands",
    "a & n islands": "Andaman & Nicobar Islands",
    "andaman": "Andaman & Nicobar Islands",
    "andaman and nicobar": "Andaman & Nicobar Islands",
    "orissa": "Odisha",
    "pondicherry": "Puducherry",
    "pondy": "Puducherry",
    "uttaranchal": "Uttarakhand",
    "tamilnadu": "Tamil Nadu",
    "chattisgarh": "Chhattisgarh",
    "chhatisgarh": "Chhattisgarh",
    "chhattisgad": "Chhattisgarh",
    "national capital territory of delhi": "Delhi",
    "all india": "India",
    "national": "India",
    "nationwide": "India",
    "country": "India",
    "bharat": "India",
}

# HMIS mixes British and American spellings and abbreviations; search for both
INDICATOR_WORDS = {
    "immunization": "immunisation",
    "immunizations": "immunisation",
    "sterilisation": "sterilization",
    "cesarean": "C-Section",
    "c section": "C-Section",
    "antenatal": "ANC",
    "prenatal": "ANC",
    "postnatal": "PNC",
}

# calls with no data behind them, and the tool that has it
DEAD_ENDS = [
    (
        lambda t, a: (
            t == "census_query" and "India" in str(a.get("state", "")).split(",")
        ),
        "census_query has no India row. For national population call census_population "
        "with state='India'; omit state here for every state.",
    ),
    (
        lambda t, a: (
            t == "census_query"
            and str(a.get("year", "")).isdigit()
            and int(a["year"]) > 2011
        ),
        "census_query covers census years 1901-2011 only. For later years call census_population.",
    ),
    (
        lambda t, a: (
            t.startswith("crs_")
            and t != "crs_population_state"
            and "India" in str(a.get("state", "")).split(",")
        ),
        "CRS has no national row, and its state rows do not sum to an official national figure. "
        "Use srs_query_bulletin for national rates or crs_population_state(state='India') for population.",
    ),
]

# district tools whose rows can be narrowed to one district after the call
DISTRICT_TOOLS = {
    "crs_district_births",
    "crs_district_deaths",
    "crs_district_infant_deaths",
    "crs_district_still_births",
    "crs_population_district",
    "census_query",
    "census_sc_st",
    "census_languages",
}

SEX_WORDS = {
    "t": "total",
    "m": "male",
    "f": "female",
    "both": "total",
    "persons": "total",
    "both sexes": "total",
    "male and female": "total",
    "males": "male",
    "females": "female",
    "men": "male",
    "women": "female",
}
# "all" means T only for MCCD
SEX_CODES = {
    **{k: v[0].upper() for k, v in SEX_WORDS.items()},
    **{k: "T" for k in ("total", "person", "all", "both_sexes")},
    "male": "M",
    "female": "F",
}
SECTOR_WORDS = {
    "combined": "total",
    "both": "total",
    "overall": "total",
    "all areas": "total",
}

# everyday names for MCCD causes, as the medical wording the data uses
CAUSE_WORDS = {
    "heart attack": "myocardial infarction",
    "heart attacks": "myocardial infarction",
    "stroke": "cerebrovascular",
    "tb": "tuberculosis",
    "suicide": "self-harm",
    "road accident": "motor vehicle traffic",
    "road accidents": "motor vehicle traffic",
    "road traffic accident": "motor vehicle traffic",
    "car accident": "motor vehicle traffic",
    "cancer": "malignant neoplasm",
    "cancers": "malignant neoplasm",
    "covid": "COVID-19",
    "coronavirus": "COVID-19",
    "high blood pressure": "hypertensive",
    "hypertension": "hypertensive",
}

YEAR_RANGE = re.compile(r"^\s*(\d{4})\s*(?:-|–|—|to|through|until)\s*(\d{4})\s*$", re.I)
SHORT_PERIOD = re.compile(r"^\s*(\d{4})\s*(?:-|–|—|:|to)\s*(\d{2}|\d{4})\s*$", re.I)
YEAR_ONLY = re.compile(r"^\s*(\d{4})\s*$")


def _types(spec: dict[str, Any]) -> set[str]:
    return {t.get("type") for t in spec.get("anyOf", [spec])} - {None, "null"}


def _enum(spec: dict[str, Any]) -> list[str]:
    return [v for t in spec.get("anyOf", [spec]) for v in t.get("enum", [])]


def _match_enum(value: str, allowed: list[str]) -> str:
    """Case-insensitive, plural-tolerant match onto an allowed value."""
    key = value.strip().lower()
    for a in allowed:
        if key in (a.lower(), a.lower() + "s"):
            return a
    return value


def _state(value: str) -> str:
    out = []
    for item in value.split(","):
        name = re.sub(
            r"^(state of|ut of)\s+|\s+(state|ut)$",
            "",
            " ".join(item.split()),
            flags=re.I,
        )
        out.append(STATE_ALIASES.get(name.lower(), name))
    return ",".join(out)


def _value(tool: str, name: str, value: Any) -> Any:
    """Per-parameter repairs, on a value already turned into a string."""
    if not isinstance(value, str):
        return value
    if name == "state":
        return _state(value)
    if name == "year":
        return ",".join(YEAR_RANGE.sub(r"\1:\2", v) for v in value.split(","))
    if name in ("period", "period1", "period2"):
        m = SHORT_PERIOD.match(value)
        if m:
            end = m.group(2) if len(m.group(2)) == 4 else m.group(1)[:2] + m.group(2)
            return f"{m.group(1)}-{end}"
    if name in ("from_date", "to_date") and YEAR_ONLY.match(value):
        # a bare year means the calendar year
        return f"{'Jan' if name == 'from_date' else 'Dec'} {value.strip()}"
    if name == "sex":
        key = value.strip().lower()
        if tool.startswith("mccd_"):
            return SEX_CODES.get(key, value)
        return SEX_WORDS.get(key, key)
    if name in ("geography", "level"):
        return value.strip().lower().rstrip("s")
    if (name == "cause" and tool.startswith("mccd_")) or (name, tool) == (
        "pattern",
        "mccd_list_causes",
    ):
        return CAUSE_WORDS.get(value.strip().lower(), value)

    if name == "sector":
        return ",".join(
            SECTOR_WORDS.get(v.strip().lower(), v.strip()) for v in value.split(",")
        )
    return value


def normalize(
    tool: str, args: dict[str, Any], schema: dict[str, Any]
) -> dict[str, Any]:
    """Return args with names, shapes and common spellings repaired for this tool's schema."""
    props: dict[str, Any] = schema.get("properties", {})
    required = set(schema.get("required", []))
    out: dict[str, Any] = {}
    for name, value in args.items():
        if name not in props:
            alias = SYNONYMS.get(name) or (
                name[:-1] if name.endswith("s") else name + "s"
            )
            if name in ("year", "years") and "year" not in props and "period" in props:
                alias = "period"
            if alias in props and alias not in args:
                name = alias
        spec = props.get(name)
        if spec is None:
            out[name] = value  # still unknown; validation reports it
            continue
        kinds = _types(spec)
        if (
            isinstance(value, str)
            and value.strip().lower() in NO_FILTER
            and name not in required
        ):
            continue
        if value is None:
            continue
        if "string" in kinds:
            if isinstance(value, (list, tuple)):
                value = ",".join(str(v).strip() for v in value if v is not None)
            elif isinstance(value, bool):
                value = str(value).lower()
            elif isinstance(value, (int, float)):
                value = str(int(value)) if float(value).is_integer() else str(value)
        elif "integer" in kinds:
            if isinstance(value, (list, tuple)) and len(value) == 1:
                value = value[0]
            if isinstance(value, str) and value.strip().lstrip("-").isdigit():
                value = int(value.strip())
            if name == "limit" and isinstance(value, int) and value > 10000:
                value = 10000
        elif "boolean" in kinds and isinstance(value, str):
            low = value.strip().lower()
            if low in ("true", "yes", "1", "y"):
                value = True
            elif low in ("false", "no", "0", "n"):
                value = False
        value = _value(tool, name, value)
        allowed = _enum(spec)
        if isinstance(value, str) and allowed:
            value = _match_enum(value, allowed)
        out[name] = value
    if (
        tool == "hmis_list_indicators"
        and isinstance(out.get("pattern"), str)
        and out.get("match", "fixed") == "fixed"
    ):
        regex = _spellings(out["pattern"])
        if regex:
            out.update(pattern=regex, match="regex")
    # the default table has no causes
    if tool == "mccd_query" and out.get("cause") and "table" not in out:
        out["table"] = "cause"
    return out


_SPELLING = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in INDICATOR_WORDS) + r")\b", re.I
)


def _spellings(pattern: str) -> str | None:
    """A regex matching pattern with each HMIS spelling variant, or None if it has none."""
    parts = _SPELLING.split(pattern)
    if len(parts) == 1:
        return None
    return "".join(
        f"({re.escape(p)}|{re.escape(INDICATOR_WORDS[p.lower()])})"
        if i % 2
        else re.escape(p)
        for i, p in enumerate(parts)
    )


def dead_end(tool: str, args: dict[str, Any]) -> str | None:
    """A message naming the right tool when this call cannot return data."""
    return next((msg for test, msg in DEAD_ENDS if test(tool, args)), None)


def _key(x: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(x).lower().replace("&", "and"))


def narrow_to_district(text: str, district: str) -> str:
    """Keep rows whose district matches; the tools have no district filter of their own."""
    data = json.loads(text)
    if not isinstance(data, dict) or "rows" not in data:
        return text
    wanted = {_key(d) for d in district.split(",") if d.strip()}
    rows = [
        r
        for r in data["rows"]
        if wanted
        & {
            _key(r.get(c))
            for c in ("district", "district_as_reported", "name")
            if r.get(c)
        }
    ]
    page_note = (
        ""
        if data.get("complete", True)
        else " Only this page was searched; pass state to see every district."
    )
    data.update(rows=rows, returned=len(rows), total_rows=len(rows))
    data.pop("next_offset", None)
    data["note"] = (
        f"Rows narrowed to district {district!r}.{page_note}"
        if rows
        else (
            f"No district matches {district!r} in these rows. Check the spelling against the "
            "district column of an unfiltered call." + page_note
        )
    )
    return to_json(data)


def _explain(tool: str, error: Exception, schema: dict[str, Any]) -> str:
    """One readable line in place of pydantic's report."""
    text = str(error)
    lines = [ln.strip() for ln in text.splitlines()]
    issues = []
    for i, ln in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if (
            ln
            and nxt
            and not ln.startswith(("For further", "1 validation", "Input"))
            and "[type=" in nxt
        ):
            issues.append(f"{ln}: {nxt.split(' [type=')[0]}")
    params = ", ".join(schema.get("properties", {}))
    detail = "; ".join(issues) if issues else text.splitlines()[0]
    return f"Invalid arguments for {tool}: {detail}. Valid parameters: {params}."


class ForgivingArguments(Middleware):
    """Normalize every tool call's arguments; rewrite validation errors to be fixable."""

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        message = context.message
        server = context.fastmcp_context.fastmcp if context.fastmcp_context else None
        tool = await server.get_tool(message.name) if server else None
        if tool is None:
            return await call_next(context)
        schema = tool.parameters
        args = dict(message.arguments or {})
        district = None
        if message.name in DISTRICT_TOOLS and "district" not in schema.get(
            "properties", {}
        ):
            district = args.pop("district", None) or args.pop("districts", None)
        message.arguments = normalize(message.name, args, schema)
        hint = dead_end(message.name, message.arguments)
        if hint:
            raise ToolError(hint)
        try:
            result = await call_next(context)
        except Exception as e:  # noqa: BLE001
            if "validation error" in str(e):
                raise ToolError(_explain(message.name, e, schema)) from e
            raise
        if district:
            if isinstance(district, (list, tuple)):
                district = ",".join(map(str, district))
            for block in result.content:
                if getattr(block, "text", None):
                    block.text = narrow_to_district(block.text, str(district))
            if (
                isinstance(result.structured_content, dict)
                and "result" in result.structured_content
            ):
                result.structured_content = {"result": result.content[0].text}
        return result


__all__ = ["ForgivingArguments", "normalize"]
