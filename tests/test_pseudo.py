# SPDX-FileCopyrightText: 2021 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Tests pseudo-ops
"""

from pytest_helpers import assert_pio_kwargs, assert_assembly_fails


def test_offset() -> None:
    assert_pio_kwargs(".origin 7", offset=7, sideset_enable=False)
    assert_assembly_fails("nop\n.origin 7")
