# SPDX-FileCopyrightText: 2021 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Tests nop
"""

from pytest_helpers import assert_assembles_to, assert_assembly_fails, assert_pio_kwargs


def test_nonsense():
    assert_assembly_fails("nope")


def test_nop():
    assert_assembles_to("nop", [0b101_00000_010_00_010])
    assert_assembles_to("nop\nnop", [0b101_00000_010_00_010, 0b101_00000_010_00_010])
    assert_assembles_to("nop [1]", [0b101_00001_010_00_010])
    assert_assembles_to("nop [31]", [0b101_11111_010_00_010])
    assert_assembles_to(".side_set 1\nnop side 1", [0b101_10000_010_00_010])
    assert_assembles_to(".side_set 1\nnop side 1 [15]", [0b101_11111_010_00_010])


def test_sideset_opt():
    assert_assembles_to(".side_set 1 opt\nnop side 1", [0b101_11000_010_00_010])
    assert_assembles_to(".side_set 1 opt\nnop side 0", [0b101_10000_010_00_010])
    assert_assembles_to(".side_set 1 opt\nnop side 0 [1]", [0b101_10001_010_00_010])
    assert_assembles_to(".side_set 1 opt\nnop [1]", [0b101_00001_010_00_010])
    assert_assembles_to(".side_set 1 opt\nnop [7]", [0b101_00111_010_00_010])
    assert_assembles_to(".side_set 1 opt\nnop side 1 [1]", [0b101_11001_010_00_010])
    assert_assembles_to(".side_set 1 opt\nnop side 0 [7]", [0b101_10111_010_00_010])


def test_set():
    # non happy path
    assert_assembly_fails(
        "set isr, 1", match="Invalid set destination 'isr'", errtype=ValueError
    )


def test_jmp():
    assert_assembles_to("l:\njmp l", [0b000_00000_000_00000])
    assert_assembles_to("l:\njmp 7", [0b000_00000_000_00111])
    assert_assembles_to("jmp l\nl:", [0b000_00000_000_00001])
    assert_assembles_to("jmp !x, l\nl:", [0b000_00000_001_00001])
    assert_assembles_to("jmp x--, l\nl:", [0b000_00000_010_00001])
    assert_assembles_to("jmp !y, l\nl:", [0b000_00000_011_00001])
    assert_assembles_to("jmp y--, l\nl:", [0b000_00000_100_00001])
    assert_assembles_to("jmp x!=y, l\nl:", [0b000_00000_101_00001])
    assert_assembles_to("jmp pin, l\nl:", [0b000_00000_110_00001])
    assert_assembles_to("jmp !osre, l\nl:", [0b000_00000_111_00001])
    # non happy path
    assert_assembly_fails(
        "jmp x--., l\nl:", match="Invalid jmp condition 'x--.'", errtype=ValueError
    )


def test_wait():
    assert_assembles_to("wait 0 gpio 0", [0b001_00000_0_00_00000])
    assert_assembles_to("wait 0 gpio 1", [0b001_00000_0_00_00001])
    assert_assembles_to("wait 1 gpio 2", [0b001_00000_1_00_00010])
    assert_assembles_to("wait 0 pin 0", [0b001_00000_0_01_00000])
    assert_assembles_to("wait 0 pin 1", [0b001_00000_0_01_00001])
    assert_assembles_to("wait 1 pin 2", [0b001_00000_1_01_00010])
    assert_assembles_to("wait 0 irq 0", [0b001_00000_0_10_00000])
    assert_assembles_to("wait 0 irq 0 rel", [0b001_00000_0_10_10000])
    assert_assembles_to("wait 1 irq 0", [0b001_00000_1_10_00000])
    assert_assembles_to("wait 0 irq 1 rel", [0b001_00000_0_10_10001])


def test_limits():
    assert_assembly_fails(".side_set 1\nnop side 2")
    assert_assembly_fails(".side_set 1\nnop side 2 [1]")
    assert_assembly_fails("nop [32]")
    assert_assembly_fails(".side_set 1\nnop side 0 [16]")
    assert_assembly_fails(".side_set 1 opt\nnop side 0 [8]")


def test_cls():
    assert_pio_kwargs("", sideset_enable=False)
    assert_pio_kwargs(".side_set 1", sideset_pin_count=1, sideset_enable=False)
    assert_pio_kwargs(".side_set 3 opt", sideset_pin_count=3, sideset_enable=True)
