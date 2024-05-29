# SPDX-FileCopyrightText: KB Sriram
#
# SPDX-License-Identifier: MIT

"""
Tests out
"""

import pytest
from pytest_helpers import assert_assembles_to, assert_assembly_fails


@pytest.mark.parametrize(
    "destination,expected",
    [
        ("pins", 0b000),
        ("x", 0b001),
        ("y", 0b010),
        ("null", 0b011),
        ("pindirs", 0b100),
        ("pc", 0b101),
        ("isr", 0b110),
        ("exec", 0b111),
    ],
)
def test_out_destinations(destination: str, expected: int) -> None:
    #                delay dst bitcount
    encoding = 0b011_00000_000_10001
    # add in the expected destination
    encoding |= expected << 5
    assert_assembles_to(f"out {destination}, 17", [encoding])


@pytest.mark.parametrize("delay", [0, 1, 9, 17, 31])
def test_out_delay(delay: int) -> None:
    #                delay dst bitcount
    encoding = 0b011_00000_000_10001
    # add in the expected delay
    encoding |= delay << 8
    assert_assembles_to(f"out pins, 17 [{delay}]", [encoding])


@pytest.mark.parametrize("bitcount", [1, 9, 17, 32])
def test_out_bitcount(bitcount: int) -> None:
    #                delay dst bitcount
    encoding = 0b011_00000_000_00000
    # add in the expected bitcount. Note that
    # 32 should be encoded as 0, which we do by
    # masking the bitcount with 0x1f
    encoding |= bitcount & 0x1F
    assert_assembles_to(f"out pins, {bitcount}", [encoding])


def test_out_delay_with_sideset() -> None:
    source = [
        ".side_set 2",
        "out pins 17 side 2 [5]",
    ]
    assert_assembles_to("\n".join(source), [0b011_10_101_000_10001])


def test_out_bad_destination() -> None:
    assert_assembly_fails(
        "out bad, 17", match="Invalid out destination 'bad'", errtype=ValueError
    )


def test_out_bad_bitcount() -> None:
    assert_assembly_fails(
        "out pins, 0", match="Count out of range", errtype=RuntimeError
    )
