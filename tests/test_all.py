# SPDX-FileCopyrightText: 2024 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import pytest
from pytest_helpers import assert_assembles_to

import all_pio_instructions


def _assert_one(expected, instruction_in, fifo="putget"):
    program = f"""
        .program all_pio
        .pio_version 1
        .fifo {fifo}
        {instruction_in}
        """
    assert_assembles_to(program, [expected])


def assert_one(expected, instruction_in):
    if isinstance(instruction_in, str):
        return _assert_one(expected, instruction_in)
    return _assert_one(expected, instruction_in[0], **instruction_in[1])


@pytest.mark.parametrize("arg", all_pio_instructions.all_instruction.items())
def test_all(arg):
    expected = arg[0]
    instruction = arg[1]
    assert_one(expected, instruction)
