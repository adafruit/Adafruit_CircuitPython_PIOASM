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


def test_sideset_pindirs() -> None:
    assert_pio_kwargs(
        ".side_set 2 opt pindirs",
        sideset_pin_count=2,
        sideset_enable=True,
        sideset_pindirs=True,
    )
    assert_pio_kwargs(
        ".side_set 2 pindirs",
        sideset_pin_count=2,
        sideset_enable=False,
        sideset_pindirs=True,
    )
    # Setting not emitted (as =False) for backwards compat
    assert_pio_kwargs(".side_set 2", sideset_pin_count=2, sideset_enable=False)
