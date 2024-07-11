# SPDX-FileCopyrightText: KB Sriram
#
# SPDX-License-Identifier: MIT

"""
Tests out
"""

from pytest_helpers import assert_assembly_fails


def test_invalid_sideset() -> None:
    source = [
        ".side_set 2",
        "side 2 [5]",
    ]
    assert_assembly_fails(
        "\n".join(source), match="Unknown instruction: side", errtype=RuntimeError
    )

    source = [
        ".side_set 2",
        "side 2",
    ]
    assert_assembly_fails(
        "\n".join(source), match="Unknown instruction: side", errtype=RuntimeError
    )


def test_invalid_delay() -> None:
    assert_assembly_fails(
        "[5]", match=r"Unknown instruction: \[5\]", errtype=RuntimeError
    )


def test_invalid_instruction() -> None:
    assert_assembly_fails(
        "bad", match=r"Unknown instruction: bad", errtype=RuntimeError
    )
