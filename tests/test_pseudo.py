# SPDX-FileCopyrightText: 2021 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Tests pseudo-ops
"""

from pytest_helpers import assert_pio_kwargs


def test_offset():
    assert_pio_kwargs(".offset 7", offset=7, sideset_enable=False)
