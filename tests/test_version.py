# SPDX-FileCopyrightText: 2024 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Tests version dependent instructions
"""

from pytest_helpers import assert_pio_kwargs, assert_assembly_fails, assert_assembles_to


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


def test_dot_set() -> None:
    assert_pio_kwargs(".set 32", sideset_enable=0)
    assert_assembly_fails(".set 16")
    assert_pio_kwargs(
        ".pio_version 1\n.set 16 right", pio_version=1, sideset_enable=0, set_count=16
    )


def test_irq_v1() -> None:
    assert_assembly_fails("irq 7 next")
    assert_assembles_to(".pio_version 1\nirq 5 next", [0b110_00000_0_0_0_11_101])
    assert_assembles_to(".pio_version 1\nirq wait 1 prev", [0b110_00000_0_0_1_01_001])


def test_mov_v1() -> None:
    assert_assembly_fails("mov osr, rxfifo[y]")
    assert_assembly_fails(".pio_version 1\nmov osr, rxfifo[y]")
    prefix = ".pio_version 1\n.fifo putget\n"
    assert_assembly_fails(prefix + "mov osr, rxfifo[8]")
    assert_assembles_to(prefix + "mov rxfifo[y], isr", [0b100_00000_0001_1_000])
    assert_assembles_to(prefix + "mov osr, rxfifo[1]", [0b100_00000_1001_0_001])
