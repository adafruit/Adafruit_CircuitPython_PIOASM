# SPDX-FileCopyrightText: 2024 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Tests version dependent instructions
"""

from pytest_helpers import assert_pio_kwargs, assert_assembly_fails


def test_version() -> None:
    assert_pio_kwargs(".pio_version 0", sideset_enable=0)
    assert_pio_kwargs(".pio_version 1", pio_version=1, sideset_enable=0)
    assert_assembly_fails(".pio_version muffin", errtype=ValueError)
    assert_assembly_fails(".pio_version -1")


def test_fifo() -> None:
    assert_pio_kwargs(".fifo txrx", sideset_enable=0)
    assert_assembly_fails(".fifo txput")
    assert_pio_kwargs(
        ".pio_version 1\n.fifo txput",
        pio_version=1,
        sideset_enable=0,
        fifo_type="txput",
    )
