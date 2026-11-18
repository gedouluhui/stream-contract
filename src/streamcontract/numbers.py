"""Numeric limits applied before expensive JSON conversion or publication."""
import math

MAX_INTEGER_BITS = 4096
MAX_INTEGER_DIGITS = 1234  # ceil(4096 * log10(2)); bit check resolves the boundary.


def check_integer(value: int) -> int:
    if value.bit_length() > MAX_INTEGER_BITS:
        raise ValueError('integer exceeds 4096-bit budget')
    return value


def parse_integer(text: str) -> int:
    if len(text) - int(text.startswith('-')) > MAX_INTEGER_DIGITS:
        raise ValueError('integer exceeds decimal digit budget')
    return check_integer(int(text))


def parse_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError('JSON number is not finite')
    return value
