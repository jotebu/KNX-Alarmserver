"""Explicit local codecs that supplement the pinned xknx registry."""

from xknx.dpt.dpt_5 import DPTValue1ByteUnsigned


class DPT20EnumNumber(DPTValue1ByteUnsigned):
    """Bare DPT 20: unsigned enum code only, no assumed subtype or label."""

    dpt_main_number = 20
    dpt_sub_number = None
    value_type = 'enum_number'
    unit = None
