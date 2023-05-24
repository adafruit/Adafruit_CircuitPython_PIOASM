# SPDX-FileCopyrightText: 2021 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Tests wrap
"""

from pytest_helpers import assert_assembly_fails, assert_pio_kwargs


def test_wrap():
    assert_assembly_fails(".wrap")
    assert_pio_kwargs(
        "nop\n.wrap_target\nnop\nnop\n.wrap",
        sideset_enable=False,
        wrap=2,
        wrap_target=1,
    )
