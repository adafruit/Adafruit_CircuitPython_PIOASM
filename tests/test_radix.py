# SPDX-FileCopyrightText: 2021 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Tests radix
"""

from pytest_helpers import assert_assembles_to


def test_octal():
    assert_assembles_to(".side_set 0o1\nset x, 0o11", [0b111_00000_001_01001])


def test_binary():
    assert_assembles_to(".side_set 0b101\nnop side 0b10001", [0b101_10001_010_00_010])


def test_hex():
    assert_assembles_to(".side_set 0x0\nnop [0x10]", [0b101_10000_010_00_010])
