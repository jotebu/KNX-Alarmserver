"""Typed alarm rules. Numeric thresholds have symmetric clear hysteresis."""

from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time
from enum import Enum
import json
import math

OPERATORS = {"eq", "ne", "gt", "ge", "lt", "le", "between", "outside", "contains", "in", "monitor"}


def normalized(value):
    if isinstance(value, Enum):
        return normalized(value.value)
    if hasattr(value, "as_dict"):
        return normalized(value.as_dict())
    if is_dataclass(value):
        return normalized(asdict(value))
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): normalized(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalized(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Nicht endlicher KNX-Wert")
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise ValueError(f"Werttyp nicht serialisierbar: {type(value).__name__}")


def numeric(value):
    return type(value) in (int, float) and math.isfinite(value)


def selected(value, field):
    for part in field.split(".") if field else []:
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdecimal() and int(part) < len(value):
            value = value[int(part)]
        else:
            raise ValueError(f"DPT-Feld nicht vorhanden: {field}")
    if value is None:
        raise ValueError("DPT-Feld ist ungueltig oder nicht vorhanden")
    return value


def same(a, b):
    # JSON booleans deliberately accept binary 0/1 for convenient DPT 1 rules.
    return type(a) is type(b) and a == b or isinstance(a, (int, float, bool)) and isinstance(b, (int, float, bool)) and a == b


def validate_rule(alarm):
    op, target, h = alarm.operator, alarm.threshold, alarm.hysteresis
    if op not in OPERATORS or not numeric(h) or h < 0:
        raise ValueError("Ungueltiger Operator oder Hysterese")
    if h and op not in {"gt", "ge", "lt", "le", "between", "outside"}:
        raise ValueError("Hysterese nur bei numerischen Grenzwerten")
    if op in {"gt", "ge", "lt", "le"} and not numeric(target):
        raise ValueError("Numerischer Grenzwert erforderlich")
    if op in {"between", "outside"}:
        if not isinstance(target, list) or len(target) != 2 or not all(numeric(v) for v in target) or target[0] >= target[1]:
            raise ValueError("Bereich benoetigt [unterer, oberer] mit unterer < oberer")
        if h * 2 >= target[1] - target[0]:
            raise ValueError("Hysterese muss kleiner als die halbe Bereichsbreite sein")
    if op == "contains" and not isinstance(target, str):
        raise ValueError("contains benoetigt Text")
    if op == "in" and (not isinstance(target, list) or not target):
        raise ValueError("in benoetigt eine nicht leere JSON-Liste")


def evaluate(alarm, value, was_active=False):
    op = alarm.operator
    if op == "monitor":
        return False
    value = selected(value, alarm.field)
    target, h = alarm.threshold, alarm.hysteresis if was_active else 0
    if op in {"gt", "ge", "lt", "le", "between", "outside"} and not numeric(value):
        raise ValueError("Numerische Regel auf nicht numerischem Wert")
    if op == "eq":
        return same(value, target)
    if op == "ne":
        return not same(value, target)
    if op == "gt":
        return value > target - h
    if op == "ge":
        return value >= target - h
    if op == "lt":
        return value < target + h
    if op == "le":
        return value <= target + h
    if op == "between":
        return target[0] - h <= value <= target[1] + h
    if op == "outside":
        return value < target[0] + h or value > target[1] - h
    if op == "contains":
        if not isinstance(value, str):
            raise ValueError("Textregel auf nicht textuellem Wert")
        return target in value
    if op == "in":
        return any(same(value, candidate) for candidate in target)
    raise ValueError("Unbekannter Operator")


def threshold_from_text(text):
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = text
    return normalized(value)
