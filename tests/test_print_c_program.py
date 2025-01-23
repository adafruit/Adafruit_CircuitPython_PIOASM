# SPDX-FileCopyrightText: 2025 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import contextlib
import io

import adafruit_pioasm


def test_print_c_program():
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        adafruit_pioasm.Program(".side_set 1 opt").print_c_program("mood")
    c_program = output.getvalue()
    assert "True" not in c_program
    assert "sideset_enable = 1" in c_program
