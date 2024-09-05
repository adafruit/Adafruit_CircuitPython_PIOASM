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


def test_mov_status() -> None:
    assert_pio_kwargs(
        ".mov_status txfifo < 5",
        sideset_enable=0,
        mov_status_type="txfifo",
        mov_status_count=5,
        mov_status_param=0,
    )
    assert_pio_kwargs(
        ".mov_status rxfifo < 8",
        sideset_enable=0,
        mov_status_type="rxfifo",
        mov_status_count=8,
        mov_status_param=0,
    )
    assert_assembly_fails(".mov_status rxfifo < -1")
    assert_assembly_fails(".mov_status rxfifo < 16")
    assert_assembly_fails(".mov_status irq next set 3")
    assert_pio_kwargs(
        ".pio_version 1\n.mov_status irq next set 3",
        pio_version=1,
        sideset_enable=0,
        mov_status_type="irq",
        mov_status_count=3,
        mov_status_param=2,
    )
    assert_pio_kwargs(
        ".pio_version 1\n.mov_status irq set 3",
        pio_version=1,
        sideset_enable=0,
        mov_status_type="irq",
        mov_status_count=3,
        mov_status_param=0,
    )
