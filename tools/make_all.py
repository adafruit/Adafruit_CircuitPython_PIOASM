# SPDX-FileCopyrightText: 2024 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Generate test cases for adafruit_pioasm, with expected results from sdk pioasm
"""

# pylint: disable=missing-function-docstring

import re
from subprocess import check_output

PIOASM = (
    "/home/jepler/src/circuitpython/ports/raspberrypi/sdk/tools/pioasm/build/pioasm"
)


def assemble_one_instruction(instruction_in):
    if isinstance(instruction_in, str):
        return _assemble_one_instruction(instruction_in)
    return _assemble_one_instruction(instruction_in[0], **instruction_in[1])


def _assemble_one_instruction(instruction_in, fifo="putget"):
    nops = "\n".join("nop" for _ in range(31))
    program = f"""
        .program all_pio
        .pio_version 1
        .fifo {fifo}
        {instruction_in}
        {nops}
        """
    output = check_output(
        [PIOASM, "/dev/stdin", "/dev/stdout"], input=program, encoding="utf-8"
    )
    return int(re.search("0x[0-9a-f]{4}", output).group(0), 16)


def all_jmp():
    for i in range(32):
        yield f"jmp {i}"
        for cond in "!x", "x--", "!y", "y--", "x!=y", "pin", "!osre":
            yield f"jmp {cond} {i}"


def all_wait():
    for polarity in range(2):
        yield f"wait {polarity} jmppin"
        for source in "gpio", "pin":
            for i in range(32):
                yield f"wait {polarity} {source} {i}"
        for i in range(8):
            yield f"wait {polarity} irq {i} rel"
            for what in "prev", "next":
                yield f"wait {polarity} irq {what} {i}"
        for i in range(1, 4):
            yield f"wait {polarity} jmppin + {i}"


def all_in():
    for source in "pins", "x", "y", "null", "isr", "osr":
        for bit_count in range(1, 33):
            yield f"in {source} {bit_count}"


def all_out():
    for dest in "pins", "x", "y", "null", "pindirs", "pc", "isr", "exec":
        for bit_count in range(1, 33):
            yield f"out {dest} {bit_count}"


def all_push():
    yield "push", {"fifo": "txrx"}
    yield "push iffull block", {"fifo": "txrx"}
    yield "push iffull noblock", {"fifo": "txrx"}


def all_pull():
    yield "pull", {"fifo": "txrx"}
    yield "pull ifempty block", {"fifo": "txrx"}
    yield "pull ifempty noblock", {"fifo": "txrx"}


def all_mov():
    for dest in ("pins", "x", "y", "pindirs", "exec", "pc", "isr", "osr"):
        for source in ("pins", "x", "y", "null", "status", "isr", "osr"):
            for operator in "", "~", "::":
                yield f"mov {dest} {operator}{source}"
    for where in 0, 1, 2, 3, "y":
        yield f"mov rxfifo[{where}], isr"
        yield f"mov osr, rxfifo[{where}]"


def all_irq():
    for i in range(8):
        yield f"irq {i}"
        yield f"irq {i} rel"
        for what in "prev", "next":
            yield f"irq {what} {i}"


def all_set():
    for dest in ("pins", "x", "y", "pindirs"):
        for i in range(32):
            yield f"set {dest} {i}"


def all_instructions():
    yield from all_jmp()
    yield from all_wait()
    yield from all_in()
    yield from all_out()
    yield from all_push()
    yield from all_pull()
    yield from all_mov()
    yield from all_irq()
    yield from all_set()


if __name__ == "__main__":
    print(
        """\
# SPDX-FileCopyrightText: 2024 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# pylint: disable=too-many-lines
# fmt: off
"""
    )
    print("all_instruction = {")
    for instr in all_instructions():
        assembled = assemble_one_instruction(instr)
        print(f"    {assembled}: {instr!r},")
    print("}")
