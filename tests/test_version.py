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
    assert_pio_kwargs(".fifo txrx", sideset_enable=0, fifo_type="txrx")
    assert_pio_kwargs(".fifo auto", sideset_enable=0)
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
        mov_status_n=5,
    )
    assert_pio_kwargs(
        ".mov_status rxfifo < 8",
        sideset_enable=0,
        mov_status_type="rxfifo",
        mov_status_n=8,
    )
    assert_assembly_fails(".mov_status rxfifo < -1")
    assert_assembly_fails(".mov_status rxfifo < 33")
    assert_assembly_fails(".mov_status irq next set 3")
    assert_pio_kwargs(
        ".pio_version 1\n.mov_status irq prev set 3",
        pio_version=1,
        sideset_enable=0,
        mov_status_type="irq",
        mov_status_n=3 | 0x8,
    )
    assert_pio_kwargs(
        ".pio_version 1\n.mov_status irq next set 3",
        pio_version=1,
        sideset_enable=0,
        mov_status_type="irq",
        mov_status_n=3 | 0x10,
    )
    assert_pio_kwargs(
        ".pio_version 1\n.mov_status irq set 3",
        pio_version=1,
        sideset_enable=0,
        mov_status_type="irq",
        mov_status_n=3,
    )
    assert_assembly_fails(".pio_version 1\n.mov_status irq prev set 9")


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
        in_pin_count=16,
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
    assert_pio_kwargs(
        ".out 16 right",
        sideset_enable=0,
        out_pin_count=16,
        auto_pull=False,
        out_shift_right=True,
    )


def test_dot_set() -> None:
    assert_pio_kwargs(".set 5", sideset_enable=0, set_pin_count=5)
    assert_assembly_fails(".set 16")
    assert_assembly_fails(".pio_version 1\n.set 16")
    assert_assembly_fails(".set 3")
    assert_pio_kwargs(
        ".pio_version 1\n.set 3 right", pio_version=1, sideset_enable=0, set_pin_count=3
    )


def test_irq_v1() -> None:
    assert_assembly_fails("irq next 7")
    assert_assembly_fails(".pio_version 1\nirq next 7 rel")
    assert_assembles_to(".pio_version 1\nirq next 5", [0b110_00000_0_0_0_11_101])
    assert_assembles_to(".pio_version 1\nirq wait prev 1", [0b110_00000_0_0_1_01_001])


def test_mov_v1() -> None:
    assert_assembly_fails("mov osr, rxfifo[y]")
    assert_assembly_fails(".pio_version 1\nmov osr, rxfifo[y]")
    prefix = ".pio_version 1\n.fifo putget\n"
    assert_assembly_fails(prefix + "mov osr, rxfifo[8]")
    assert_assembles_to(prefix + "mov rxfifo[y], isr", [0b100_00000_0001_0_000])
    assert_assembles_to(prefix + "mov osr, rxfifo[1]", [0b100_00000_1001_1_001])

    assert_assembly_fails("mov pindirs, null", errtype=ValueError)
    assert_assembles_to(prefix + "mov pindirs, null", [0b101_00000_01100011])


def test_wait_v1() -> None:
    assert_assembly_fails("wait 0 jmppin")
    assert_assembly_fails("wait 0 irq next 5")
    prefix = ".pio_version 1\n"
    assert_assembly_fails(prefix + "wait 0 jmppin +")
    assert_assembly_fails(prefix + "wait 0 jmppin + 7")
    assert_assembles_to(prefix + "wait 0 jmppin + 3", [0b001_00000_0_11_00011])
    assert_assembles_to(prefix + "wait 1 jmppin", [0b001_00000_1_11_00000])

    assert_assembles_to(prefix + "wait 0 irq next 5", [0b001_00000_0_10_11_101])
    assert_assembles_to(prefix + "wait 1 irq prev 4", [0b001_00000_1_10_01_100])
