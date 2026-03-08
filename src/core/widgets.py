"""
Widget Service.

Provides inline widgets for special queries (calculator, weather, definitions, etc.)
similar to Perplexica's widget system.
"""

import math
import re
from dataclasses import dataclass, field
from typing import Optional, Any

from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WidgetResult:
    """Result from a widget evaluation."""
    widget_type: str
    title: str
    data: dict[str, Any]
    display_text: str

    def to_dict(self) -> dict:
        return {
            "type": self.widget_type,
            "title": self.title,
            "data": self.data,
            "displayText": self.display_text,
        }


def try_widget(query: str) -> Optional[WidgetResult]:
    """
    Attempt to resolve a query with a widget.

    Returns None if no widget matches.
    """
    q = query.strip()

    result = _try_calculator(q)
    if result:
        return result

    result = _try_unit_conversion(q)
    if result:
        return result

    result = _try_definition(q)
    if result:
        return result

    return None


# ----------------------------------------------------------------
# Calculator widget
# ----------------------------------------------------------------

_CALC_PATTERN = re.compile(
    r"^[\d\s\.\+\-\*/\(\)\^%]+$"
)

_CALC_FUNC_PATTERN = re.compile(
    r"^(?:calculate|compute|solve|what is|eval)\s+(.+)$", re.IGNORECASE
)


def _try_calculator(query: str) -> Optional[WidgetResult]:
    """Evaluate simple math expressions safely."""
    expr = query

    # Check for "calculate X" prefix
    m = _CALC_FUNC_PATTERN.match(query)
    if m:
        expr = m.group(1).strip()

    # Must look like a math expression
    if not _CALC_PATTERN.match(expr):
        return None

    # Safe evaluation: replace ^ with ** for exponentiation
    expr_safe = expr.replace("^", "**")

    try:
        # Use eval with restricted builtins — only math operations
        allowed_names = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "pow": pow,
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "log10": math.log10,
            "pi": math.pi,
            "e": math.e,
        }
        result = eval(expr_safe, {"__builtins__": {}}, allowed_names)  # noqa: S307
    except Exception:
        return None

    return WidgetResult(
        widget_type="calculator",
        title="Calculator",
        data={"expression": query, "result": result},
        display_text=f"{query} = {result}",
    )


# ----------------------------------------------------------------
# Unit conversion widget
# ----------------------------------------------------------------

_CONVERSION_PATTERNS = [
    # Temperature: "32 F to C", "100 celsius to fahrenheit"
    (
        re.compile(
            r"([\d.]+)\s*(?:degrees?\s*)?(f|fahrenheit|c|celsius|k|kelvin)\s+(?:to|in)\s+(f|fahrenheit|c|celsius|k|kelvin)",
            re.IGNORECASE,
        ),
        "temperature",
    ),
    # Distance: "5 miles to km"
    (
        re.compile(
            r"([\d.]+)\s*(miles?|mi|km|kilometers?|m|meters?|ft|feet|cm|centimeters?|in|inches?)\s+(?:to|in)\s+(miles?|mi|km|kilometers?|m|meters?|ft|feet|cm|centimeters?|in|inches?)",
            re.IGNORECASE,
        ),
        "distance",
    ),
    # Weight: "5 kg to lbs"
    (
        re.compile(
            r"([\d.]+)\s*(kg|kilograms?|lbs?|pounds?|g|grams?|oz|ounces?)\s+(?:to|in)\s+(kg|kilograms?|lbs?|pounds?|g|grams?|oz|ounces?)",
            re.IGNORECASE,
        ),
        "weight",
    ),
]

# Conversion factors to base unit
_TEMP_MAP = {"f": "F", "fahrenheit": "F", "c": "C", "celsius": "C", "k": "K", "kelvin": "K"}
_DIST_TO_METERS = {
    "miles": 1609.344, "mile": 1609.344, "mi": 1609.344,
    "km": 1000, "kilometers": 1000, "kilometer": 1000,
    "m": 1, "meters": 1, "meter": 1,
    "ft": 0.3048, "feet": 0.3048,
    "cm": 0.01, "centimeters": 0.01, "centimeter": 0.01,
    "in": 0.0254, "inches": 0.0254, "inch": 0.0254,
}
_WEIGHT_TO_GRAMS = {
    "kg": 1000, "kilograms": 1000, "kilogram": 1000,
    "lbs": 453.592, "lb": 453.592, "pounds": 453.592, "pound": 453.592,
    "g": 1, "grams": 1, "gram": 1,
    "oz": 28.3495, "ounces": 28.3495, "ounce": 28.3495,
}


def _convert_temp(value: float, from_unit: str, to_unit: str) -> float:
    f, t = _TEMP_MAP.get(from_unit.lower(), "C"), _TEMP_MAP.get(to_unit.lower(), "C")
    # Convert to Celsius first
    if f == "F":
        celsius = (value - 32) * 5 / 9
    elif f == "K":
        celsius = value - 273.15
    else:
        celsius = value
    # Convert from Celsius to target
    if t == "F":
        return celsius * 9 / 5 + 32
    if t == "K":
        return celsius + 273.15
    return celsius


def _try_unit_conversion(query: str) -> Optional[WidgetResult]:
    for pattern, conv_type in _CONVERSION_PATTERNS:
        m = pattern.search(query)
        if not m:
            continue
        value = float(m.group(1))
        from_unit = m.group(2).lower()
        to_unit = m.group(3).lower()

        if conv_type == "temperature":
            result = _convert_temp(value, from_unit, to_unit)
        elif conv_type == "distance":
            in_meters = value * _DIST_TO_METERS.get(from_unit, 1)
            result = in_meters / _DIST_TO_METERS.get(to_unit, 1)
        elif conv_type == "weight":
            in_grams = value * _WEIGHT_TO_GRAMS.get(from_unit, 1)
            result = in_grams / _WEIGHT_TO_GRAMS.get(to_unit, 1)
        else:
            continue

        result = round(result, 4)
        return WidgetResult(
            widget_type="conversion",
            title=f"Unit Conversion ({conv_type})",
            data={
                "value": value,
                "from_unit": from_unit,
                "to_unit": to_unit,
                "result": result,
                "type": conv_type,
            },
            display_text=f"{value} {from_unit} = {result} {to_unit}",
        )
    return None


# ----------------------------------------------------------------
# Definition widget
# ----------------------------------------------------------------

_DEFINE_PATTERN = re.compile(
    r"^(?:define|definition of|what does .+ mean|meaning of)\s+(.+)$",
    re.IGNORECASE,
)


def _try_definition(query: str) -> Optional[WidgetResult]:
    """Detect definition queries — actual definition fetched by LLM."""
    m = _DEFINE_PATTERN.match(query)
    if not m:
        return None
    term = m.group(1).strip().rstrip("?.")
    return WidgetResult(
        widget_type="definition",
        title=f"Define: {term}",
        data={"term": term},
        display_text=f"Looking up definition of '{term}'...",
    )
