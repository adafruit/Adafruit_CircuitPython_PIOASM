# SPDX-FileCopyrightText: 2024 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Tests out
"""

from pytest_helpers import assert_assembly_fails
import adafruit_pioasm


def test_label() -> None:
    source = [
        "    jmp label1",
        "label1:",
        "    jmp label2",
        "public label2:",
        "    nop",
    ]
    program = adafruit_pioasm.Program("\n".join(source))
    assert program.public_labels == {"label2": 2}

    # Test each combination of public/privagte label duplication
    source = [
        "label1:\n",
        "nop\n",
        "public label1:\n",
        "nop\n",
    ]
    assert_assembly_fails(
        "\n".join(source), match="Duplicate label", errtype=SyntaxError
    )

    source = [
        "label1:\n",
        "    nop\n",
        "label1:\n",
        "    nop\n",
    ]
    assert_assembly_fails(
        "\n".join(source), match="Duplicate label", errtype=SyntaxError
    )

    source = [
        "public label1:\n",
        "    nop\n",
        "label1:\n",
        "    nop\n",
    ]
    assert_assembly_fails(
        "\n".join(source), match="Duplicate label", errtype=SyntaxError
    )

    source = [
        "public label1:\n",
        "    nop\n",
        "public label1:\n",
        "    nop\n",
    ]
    assert_assembly_fails(
        "\n".join(source), match="Duplicate label", errtype=SyntaxError
    )
