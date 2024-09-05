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


def test_dot_in() -> None:
    assert_pio_kwargs(
        ".in 32 left auto 11",
        sideset_enable=0,
        auto_push=True,
        push_threshold=11,
        in_shift_right=False,
    )
    assert_assembly_fails(".in 16")
    assert_pio_kwargs(
        ".pio_version 1\n.in 16 right",
        pio_version=1,
        sideset_enable=0,
        in_count=16,
        auto_push=False,
        in_shift_right=True,
    )


def test_dot_out() -> None:
    assert_pio_kwargs(
        ".out 32 left auto 11",
        sideset_enable=0,
        auto_pull=True,
        pull_threshold=11,
        out_shift_right=False,
    )
    assert_assembly_fails(".out 16")
    assert_pio_kwargs(
        ".pio_version 1\n.out 16 right",
        pio_version=1,
        sideset_enable=0,
        out_count=16,
        auto_pull=False,
        out_shift_right=True,
    )
