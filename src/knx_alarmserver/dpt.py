"""Exact xknx DPT registry. Unsupported subtypes never fall back to a guessed base."""

from enum import Enum
from functools import lru_cache
import json

from .rules import normalized


@lru_cache(maxsize=512)
def transcoder(dpt):
    from xknx.dpt import DPTBase
    result = DPTBase.parse_transcoder(dpt)
    if result is None:
        raise ValueError(f"DPT {dpt} wird von der installierten xknx-Version nicht unterstuetzt")
    return result


def decode(dpt, payload):
    codec = transcoder(dpt)
    decoded = codec.from_knx(payload)
    value = normalized(decoded)
    display = f"{decoded.name.lower()} ({decoded.value})" if isinstance(decoded, Enum) else (
        json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value))
    return value, display, codec.unit


def catalog():
    from xknx.dpt import DPTBase
    return sorted([{"dpt": cls.dpt_number_str(), "name": cls.__name__, "unit": cls.unit}
                   for cls in DPTBase.dpt_class_tree() if cls.has_distinct_dpt_numbers()
                   and cls.dpt_main_number is not None], key=lambda item: tuple(map(int, item["dpt"].split("."))))
