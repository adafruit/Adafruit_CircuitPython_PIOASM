# SPDX-FileCopyrightText: 2021 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Tests mov
"""

from pytest_helpers import assert_assembles_to, assert_assembly_fails


def test_mov_non_happy():
    # non happy path
    assert_assembly_fails(
        "mov x, blah", match="Invalid mov source 'blah'", errtype=ValueError
    )


def test_mov_invert():
    # test moving and inverting
    assert_assembles_to("mov x, ~ x", [0b101_00000_001_01_001])
    assert_assembles_to("mov x, ~x", [0b101_00000_001_01_001])
    assert_assembles_to("mov x, !x", [0b101_00000_001_01_001])


def test_mov_reverse():
    # test moving and reversing bits
    assert_assembles_to("mov x, :: x", [0b101_00000_001_10_001])
    assert_assembles_to("mov x, ::x", [0b101_00000_001_10_001])
