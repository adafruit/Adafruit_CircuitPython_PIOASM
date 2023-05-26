# SPDX-FileCopyrightText: 2021 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Pytest helper functions
"""

import pytest

import adafruit_pioasm


def nice_opcode(opcode):
    opcode = f"{opcode:016b}"
    return opcode[:3] + "_" + opcode[3:8] + "_" + opcode[8:]


def assert_assembles_to(source, expected):
    actual = adafruit_pioasm.assemble(source)
    expected_bin = [nice_opcode(x) for x in expected]
    actual_bin = [nice_opcode(x) for x in actual]
    assert (
        expected_bin == actual_bin
    ), f"Assembling {source!r}: Expected {expected_bin}, got {actual_bin}"


def assert_assembly_fails(source, match=None, errtype=RuntimeError):
    with pytest.raises(errtype, match=match):
        adafruit_pioasm.assemble(source)
    # if match:
    #    with pytest.raises(errtype, match=match):
    #        adafruit_pioasm.assemble(source)
    # else:
    #    with pytest.raises(errtype):
    #        adafruit_pioasm.assemble(source)


def assert_pio_kwargs(source, **kw):
    program = adafruit_pioasm.Program(source)
    assert kw == program.pio_kwargs
