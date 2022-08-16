# SPDX-FileCopyrightText: Copyright (c) 2021 Scott Shawcroft for Adafruit Industries LLC
#
# SPDX-License-Identifier: MIT
"""
`adafruit_pioasm`
================================================================================

Simple assembler to convert pioasm to bytes


* Author(s): Scott Shawcroft
"""

import array
import re

splitter = re.compile(r",\s*|\s+(?:,\s*)?").split
mov_splitter = re.compile("!|~|::").split

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_PIOASM.git"

CONDITIONS = ["", "!x", "x--", "!y", "y--", "x!=y", "pin", "!osre"]
IN_SOURCES = ["pins", "x", "y", "null", None, None, "isr", "osr"]
OUT_DESTINATIONS = ["pins", "x", "y", "null", "pindirs", "pc", "isr", "exec"]
WAIT_SOURCES = ["gpio", "pin", "irq", None]
MOV_DESTINATIONS = ["pins", "x", "y", None, "exec", "pc", "isr", "osr"]
MOV_SOURCES = ["pins", "x", "y", "null", None, "status", "isr", "osr"]
MOV_OPS = [None, "~", "::", None]
SET_DESTINATIONS = ["pins", "x", "y", None, "pindirs", None, None, None]


class Program:  # pylint: disable=too-few-public-methods
    """Encapsulates a program's instruction stream and configuration flags

    Example::

        program = adafruit_pioasm.Program(...)
        state_machine = rp2pio.StateMachine(program.assembled, ..., **program.pio_kwargs)

    """

    def __init__(self, text_program: str, *, build_debuginfo=False) -> None:
        """Converts pioasm text to encoded instruction bytes"""
        # pylint: disable=too-many-branches,too-many-statements,too-many-locals
        assembled = []
        program_name = None
        labels = {}
        linemap = []
        instructions = []
        sideset_count = 0
        sideset_enable = 0
        wrap = None
        wrap_target = None
        for i, line in enumerate(text_program.split("\n")):
            line = line.strip()
            if not line:
                continue
            if ";" in line:
                line = line.split(";")[0].strip()
            if line.startswith(".program"):
                if program_name:
                    raise RuntimeError("Multiple programs not supported")
                program_name = line.split()[1]
            elif line.startswith(".wrap_target"):
                wrap_target = len(instructions)
            elif line.startswith(".wrap"):
                if len(instructions) == 0:
                    raise RuntimeError("Cannot have .wrap as first instruction")
                wrap = len(instructions) - 1
            elif line.startswith(".side_set"):
                sideset_count = int(line.split()[1], 0)
                sideset_enable = "opt" in line
            elif line.endswith(":"):
                label = line[:-1]
                if label in labels:
                    raise SyntaxError(f"Duplicate label {repr(label)}")
                labels[label] = len(instructions)
            elif line:
                # Only add as an instruction if the line isn't empty
                instructions.append(line)
                linemap.append(i)

        max_delay = 2 ** (5 - sideset_count - sideset_enable) - 1
        assembled = []
        for instruction in instructions:
            # print(instruction)
            instruction = splitter(instruction.strip())
            delay = 0
            if instruction[-1].endswith("]"):  # Delay
                delay = int(instruction[-1].strip("[]"), 0)
                if delay < 0:
                    raise RuntimeError("Delay negative:", delay)
                if delay > max_delay:
                    raise RuntimeError("Delay too long:", delay)
                instruction.pop()
            if len(instruction) > 1 and instruction[-2] == "side":
                if sideset_count == 0:
                    raise RuntimeError("No side_set count set")
                sideset_value = int(instruction[-1], 0)
                if sideset_value >= 2**sideset_count:
                    raise RuntimeError("Sideset value too large")
                delay |= sideset_value << (5 - sideset_count - sideset_enable)
                delay |= sideset_enable << 4
                instruction.pop()
                instruction.pop()

            if instruction[0] == "nop":
                #                  mov delay   y op   y
                assembled.append(0b101_00000_010_00_010)
            elif instruction[0] == "jmp":
                #                instr delay cnd addr
                assembled.append(0b000_00000_000_00000)
                target = instruction[-1]
                if target[:1] in "0123456789":
                    assembled[-1] |= int(target, 0)
                elif instruction[-1] in labels:
                    assembled[-1] |= labels[target]
                else:
                    raise SyntaxError(f"Invalid jmp target {repr(target)}")

                if len(instruction) > 2:
                    try:
                        assembled[-1] |= CONDITIONS.index(instruction[1]) << 5
                    except ValueError as exc:
                        raise ValueError(
                            f"Invalid jmp condition '{instruction[1]}'"
                        ) from exc

            elif instruction[0] == "wait":
                #                instr delay p sr index
                assembled.append(0b001_00000_0_00_00000)
                polarity = int(instruction[1], 0)
                if not 0 <= polarity <= 1:
                    raise RuntimeError("Invalid polarity")
                assembled[-1] |= polarity << 7
                assembled[-1] |= WAIT_SOURCES.index(instruction[2]) << 5
                num = int(instruction[3], 0)
                if not 0 <= num <= 31:
                    raise RuntimeError("Wait num out of range")
                assembled[-1] |= num
                if instruction[-1] == "rel":
                    assembled[-1] |= 0x10  # Set the high bit of the irq value
            elif instruction[0] == "in":
                #                instr delay src count
                assembled.append(0b010_00000_000_00000)
                assembled[-1] |= IN_SOURCES.index(instruction[1]) << 5
                count = int(instruction[-1], 0)
                if not 1 <= count <= 32:
                    raise RuntimeError("Count out of range")
                assembled[-1] |= count & 0x1F  # 32 is 00000 so we mask the top
            elif instruction[0] == "out":
                #                instr delay dst count
                assembled.append(0b011_00000_000_00000)
                assembled[-1] |= OUT_DESTINATIONS.index(instruction[1]) << 5
                count = int(instruction[-1], 0)
                if not 1 <= count <= 32:
                    raise RuntimeError("Count out of range")
                assembled[-1] |= count & 0x1F  # 32 is 00000 so we mask the top
            elif instruction[0] == "push" or instruction[0] == "pull":
                #                instr delay d i b zero
                assembled.append(0b100_00000_0_0_0_00000)
                if instruction[0] == "pull":
                    assembled[-1] |= 0x80
                if instruction[-1] == "block" or not instruction[-1].endswith("block"):
                    assembled[-1] |= 0x20
                if len(instruction) > 1 and instruction[1] in ("ifempty", "iffull"):
                    assembled[-1] |= 0x40
            elif instruction[0] == "mov":
                #                instr delay dst op src
                assembled.append(0b101_00000_000_00_000)
                assembled[-1] |= MOV_DESTINATIONS.index(instruction[1]) << 5
                source = instruction[-1]
                source_split = mov_splitter(source)
                if len(source_split) == 1:
                    try:
                        assembled[-1] |= MOV_SOURCES.index(source)
                    except ValueError as exc:
                        raise ValueError(f"Invalid mov source '{source}'") from exc
                else:
                    assembled[-1] |= MOV_SOURCES.index(source_split[1])
                    if source[:1] == "!":
                        assembled[-1] |= 0x08
                    elif source[:1] == "~":
                        assembled[-1] |= 0x08
                    elif source[:2] == "::":
                        assembled[-1] |= 0x10
                    else:
                        raise RuntimeError("Invalid mov operator:", source[:1])
                if len(instruction) > 3:
                    assembled[-1] |= MOV_OPS.index(instruction[-2]) << 3
            elif instruction[0] == "irq":
                #                instr delay z c w index
                assembled.append(0b110_00000_0_0_0_00000)
                if instruction[-1] == "rel":
                    assembled[-1] |= 0x10  # Set the high bit of the irq value
                    instruction.pop()
                num = int(instruction[-1], 0)
                if not 0 <= num <= 7:
                    raise RuntimeError("Interrupt index out of range")
                assembled[-1] |= num
                if len(instruction) == 3:  # after rel has been removed
                    if instruction[1] == "wait":
                        assembled[-1] |= 0x20
                    elif instruction[1] == "clear":
                        assembled[-1] |= 0x40
                    # All other values are the default of set without waiting
            elif instruction[0] == "set":
                #                instr delay dst data
                assembled.append(0b111_00000_000_00000)
                try:
                    assembled[-1] |= SET_DESTINATIONS.index(instruction[1]) << 5
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid set destination '{instruction[1]}'"
                    ) from exc
                value = int(instruction[-1], 0)
                if not 0 <= value <= 31:
                    raise RuntimeError("Set value out of range")
                assembled[-1] |= value
            else:
                raise RuntimeError("Unknown instruction:" + instruction[0])
            assembled[-1] |= delay << 8
            # print(bin(assembled[-1]))

        self.pio_kwargs = {
            "sideset_enable": sideset_enable,
        }

        if sideset_count != 0:
            self.pio_kwargs["sideset_pin_count"] = sideset_count

        if wrap is not None:
            self.pio_kwargs["wrap"] = wrap
        if wrap_target is not None:
            self.pio_kwargs["wrap_target"] = wrap_target

        self.assembled = array.array("H", assembled)

        if build_debuginfo:
            self.debuginfo = (linemap, text_program)
        else:
            self.debuginfo = None

    def print_c_program(self, name, qualifier="const"):
        """Print the program into a C program snippet"""
        if self.debuginfo is None:
            linemap = None
            program_lines = None
        else:
            linemap = self.debuginfo[0][:]  # Use a copy since we destroy it
            program_lines = self.debuginfo[1].split("\n")

        print(
            f"{qualifier} int {name}_wrap = {self.pio_kwargs.get('wrap', len(self.assembled)-1)};"
        )
        print(
            f"{qualifier} int {name}_wrap_target = {self.pio_kwargs.get('wrap_target', 0)};"
        )
        sideset_pin_count = self.pio_kwargs.get("sideset_pin_count", 0)
        print(f"{qualifier} int {name}_sideset_pin_count = {sideset_pin_count};")
        print(
            f"{qualifier} bool {name}_sideset_enable = {self.pio_kwargs['sideset_enable']};"
        )
        print(f"{qualifier} uint16_t {name}[] = " + "{")
        last_line = 0
        if linemap:
            for inst in self.assembled:
                next_line = linemap[0]
                del linemap[0]
                while last_line < next_line:
                    line = program_lines[last_line]
                    if line:
                        print(f"            // {line}")
                    last_line += 1
                line = program_lines[last_line]
                print(f"    0x{inst:04x}, // {line}")
                last_line += 1
            while last_line < len(program_lines):
                line = program_lines[last_line]
                if line:
                    print(f"            // {line}")
                last_line += 1
        else:
            for i in range(0, len(self.assembled), 8):
                print(
                    "    " + ", ".join("0x%04x" % i for i in self.assembled[i : i + 8])
                )
        print("};")
        print()


def assemble(program_text: str) -> array.array:
    """Converts pioasm text to encoded instruction bytes

    In new code, prefer to use the `Program` class so that the extra arguments
    such as the details about side-set pins can be easily passsed to the
    ``StateMachine`` constructor."""
    return Program(program_text).assembled
