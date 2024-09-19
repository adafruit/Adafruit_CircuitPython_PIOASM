# SPDX-FileCopyrightText: 2021 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Pytest helper functions
"""

try:
    from typing import Any, List, Optional, Type
except ImportError:
    pass

import pytest

import adafruit_pioasm


def nice_opcode(opcode: int) -> str:
    nice = f"{opcode:016b}"
    return nice[:3] + "_" + nice[3:8] + "_" + nice[8:]


def assert_assembles_to(source: str, expected: List[int]) -> None:
    actual = adafruit_pioasm.assemble(source)
    expected_bin = [nice_opcode(x) for x in expected]
    actual_bin = [nice_opcode(x) for x in actual]
    assert (
        expected_bin == actual_bin
    ), f"Assembling {source!r}: Expected {expected_bin}, got {actual_bin}"


def assert_assembly_fails(
    source: str, match: Optional[str] = None, errtype: Type[Exception] = RuntimeError
) -> None:
    with pytest.raises(errtype, match=match):
        adafruit_pioasm.assemble(source)
    # if match:
    #    with pytest.raises(errtype, match=match):
    #        adafruit_pioasm.assemble(source)
    # else:
    #    with pytest.raises(errtype):
    #        adafruit_pioasm.assemble(source)


def assert_pio_kwargs(source: str, **kw: Any) -> None:
    program = adafruit_pioasm.Program(source)
    assert (
        kw == program.pio_kwargs
    ), f"Assembling {source!r}: Expected {kw}, got {program.pio_kwargs}"
