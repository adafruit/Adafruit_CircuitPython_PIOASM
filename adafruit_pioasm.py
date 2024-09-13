# SPDX-FileCopyrightText: Copyright (c) 2021 Scott Shawcroft for Adafruit Industries LLC
#
# SPDX-License-Identifier: MIT
"""
`adafruit_pioasm`
================================================================================

Simple assembler to convert pioasm to bytes


* Author(s): Scott Shawcroft
"""

try:
    from typing import List, MutableSequence
except ImportError:
    pass

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
MOV_DESTINATIONS_V0 = ["pins", "x", "y", None, "exec", "pc", "isr", "osr"]
MOV_DESTINATIONS_V1 = ["pins", "x", "y", "pindirs", "exec", "pc", "isr", "osr"]
MOV_SOURCES = ["pins", "x", "y", "null", None, "status", "isr", "osr"]
MOV_OPS = [None, "~", "::", None]
SET_DESTINATIONS = ["pins", "x", "y", None, "pindirs", None, None, None]
FIFO_TYPES = {
    "auto": 0,
    "txrx": 0,
    "tx": 0,
    "rx": 0,
    "txput": 1,
    "txget": 1,
    "putget": 1,
}


class Program:  # pylint: disable=too-few-public-methods
    """Encapsulates a program's instruction stream and configuration flags

    Example::

        program = adafruit_pioasm.Program(...)
        state_machine = rp2pio.StateMachine(program.assembled, ..., **program.pio_kwargs)

    """

    def __init__(self, text_program: str, *, build_debuginfo: bool = False) -> None:
        """Converts pioasm text to encoded instruction bytes"""
        # pylint: disable=too-many-branches,too-many-statements,too-many-locals
        assembled: List[int] = []
        program_name = None
        labels = {}
        linemap = []
        instructions: List[str] = []
        sideset_count = 0
        sideset_enable = 0
        wrap = None
        wrap_target = None
        offset = -1
        pio_version = 0
        fifo_type = "auto"
        mov_status_type = None
        mov_status_n = None
        in_count = None
        in_shift_right = None
        auto_push = None
        push_threshold = None
        out_count = None
        out_shift_right = None
        auto_pull = None
        pull_threshold = None
        set_count = None

        def require_before_instruction():
            if len(instructions) != 0:
                raise RuntimeError(f"{words[0]} must be before first instruction")

        def require_version(required_version, instruction):
            if pio_version < required_version:
                raise RuntimeError(
                    f"{instruction} requires .pio_version {required_version}"
                )

        def int_in_range(arg, low, high, what, radix=0):
            result = int(arg, radix)
            if low <= result < high:
                return result
            raise RuntimeError(
                f"{what} must be at least {low} and no greater than {high}, got {result}"
            )

        def parse_rxfifo_brackets(arg, fifo_dir):
            require_version(1, line)
            if (  # pylint: disable=consider-using-in
                fifo_type != "putget" and fifo_type != fifo_dir
            ):
                raise RuntimeError(
                    f"FIFO must be configured for '{fifo_dir}' or 'putget' for {line}"
                )
            if arg.endswith("[y]"):
                return 0b1000
            return int_in_range(arg[7:-1], 0, 8, "rxfifo index")

        for i, line in enumerate(text_program.split("\n")):
            line = line.split(";")[0].strip()
            if not line:
                continue
            words = line.split()
            if line.startswith(".program"):
                if program_name:
                    raise RuntimeError("Multiple programs not supported")
                program_name = line.split()[1]
            elif line.startswith(".pio_version"):
                require_before_instruction()
                pio_version = int_in_range(words[1], 0, 2, ".pio_version")
            elif line.startswith(".origin"):
                require_before_instruction()
                offset = int_in_range(words[1], 0, 32, ".origin")
            elif line.startswith(".wrap_target"):
                wrap_target = len(instructions)
            elif line.startswith(".wrap"):
                if len(instructions) == 0:
                    raise RuntimeError("Cannot have .wrap as first instruction")
                wrap = len(instructions) - 1
            elif line.startswith(".side_set"):
                sideset_count = int(line.split()[1], 0)
                sideset_enable = "opt" in line
            elif line.startswith(".fifo"):
                require_before_instruction()
                fifo_type = line.split()[1]
                required_version = FIFO_TYPES.get(fifo_type)
                if required_version is None:
                    raise RuntimeError(f"Invalid fifo type {fifo_type}")
                require_version(required_version, line)
            elif line.startswith(".mov_status"):
                require_before_instruction()
                required_version = 0
                mov_status_n = 0
                mov_status_type = words[1]
                if words[1] in ("txfifo", "rxfifo"):
                    if words[2] != "<":
                        raise RuntimeError(f"Invalid {line}")
                    mov_status_n = int_in_range(words[3], 0, 32, words[1])
                elif words[1] == "irq":
                    required_version = 1
                    idx = 2
                    if words[idx] == "next":
                        mov_status_n = 0x10
                        idx += 1
                    elif words[idx] == "prev":
                        mov_status_n = 0x8
                        idx += 1
                    else:
                        mov_status_n = 0
                    if words[idx] != "set":
                        raise RuntimeError(f"Invalid {line})")
                    mov_status_n |= int_in_range(words[idx + 1], 0, 8, "mov_status irq")
                require_version(required_version, line)
            elif words[0] == ".out":
                require_before_instruction()
                out_count = int_in_range(
                    words[1], 32 if pio_version == 0 else 1, 33, ".out count"
                )
                auto_pull = False

                idx = 2
                if idx < len(words) and words[idx] == "left":
                    out_shift_right = False
                    idx += 1
                elif idx < len(words) and words[idx] == "right":
                    out_shift_right = True
                    idx += 1

                if idx < len(words) and words[idx] == "auto":
                    auto_pull = True
                    idx += 1

                if idx < len(words):
                    pull_threshold = int_in_range(words[idx], 1, 33, ".out threshold")
                    idx += 1

            elif words[0] == ".in":
                require_before_instruction()
                in_count = int_in_range(
                    words[1], 32 if pio_version == 0 else 1, 33, ".in count"
                )
                auto_push = False

                idx = 2
                if idx < len(words) and words[idx] == "left":
                    in_shift_right = False
                    idx += 1
                elif idx < len(words) and words[idx] == "right":
                    in_shift_right = True
                    idx += 1

                if idx < len(words) and words[idx] == "auto":
                    auto_push = True
                    idx += 1

                if idx < len(words):
                    push_threshold = int_in_range(words[idx], 1, 33, ".in threshold")
                    idx += 1

            elif words[0] == ".set":
                require_before_instruction()
                set_count = int_in_range(
                    words[1], 5 if pio_version == 0 else 1, 6, ".set count"
                )

            elif line.endswith(":"):
                label = line[:-1]
                if label in labels:
                    raise SyntaxError(f"Duplicate label {repr(label)}")
                labels[label] = len(instructions)
            elif line:
                # Only add as an instruction if the line isn't empty
                instructions.append(line)
                linemap.append(i)

        if pio_version >= 1:
            mov_destinations = MOV_DESTINATIONS_V1
        else:
            mov_destinations = MOV_DESTINATIONS_V0

        max_delay = 2 ** (5 - sideset_count - sideset_enable) - 1
        assembled = []
        for line in instructions:
            instruction = splitter(line.strip())
            delay = 0
            if (
                len(instruction) > 1
                and instruction[-1].startswith("[")
                and instruction[-1].endswith("]")
            ):  # Delay
                delay = int(instruction[-1].strip("[]"), 0)
                if delay < 0:
                    raise RuntimeError("Delay negative:", delay)
                if delay > max_delay:
                    raise RuntimeError("Delay too long:", delay)
                instruction.pop()
            if len(instruction) > 2 and instruction[-2] == "side":
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
                source = instruction[2]
                if not 0 <= polarity <= 1:
                    raise RuntimeError("Invalid polarity")
                assembled[-1] |= polarity << 7
                if instruction[2] == "jmppin":
                    require_version(1, "wait jmppin")
                    num = 0
                    print("wait jmppin", instruction)
                    if len(instruction) > 3:
                        if len(instruction) < 5 or instruction[3] != "+":
                            raise RuntimeError("invalid wait jmppin")
                        num = int_in_range(instruction[4], 0, 4, "wait jmppin offset")
                    assembled[-1] |= num
                    assembled[-1] |= 0b11 << 5  # JMPPIN wait source
                else:
                    assembled[-1] |= WAIT_SOURCES.index(instruction[2]) << 5
                    num = int(instruction[3], 0)
                    if not 0 <= num <= 31:
                        raise RuntimeError("Wait num out of range")
                    assembled[-1] |= num
                    # The flag index is decoded in the same way as the IRQ
                    # index field, decoding down from the two MSBs
                    if instruction[-1] == "next":
                        require_version(1, "wait irq next")
                        assembled[-1] |= 0b11000
                    elif instruction[-1] == "prev":
                        require_version(1, "wait irq prev")
                        assembled[-1] |= 0b01000
                    elif instruction[-1] == "rel":
                        assembled[-1] |= 0b10000
            elif instruction[0] == "in":
                #                instr delay src count
                assembled.append(0b010_00000_000_00000)
                source = instruction[1]
                try:
                    assembled[-1] |= IN_SOURCES.index(source) << 5
                except ValueError as exc:
                    raise ValueError(f"Invalid in source '{source}'") from exc
                count = int(instruction[-1], 0)
                if not 1 <= count <= 32:
                    raise RuntimeError("Count out of range")
                assembled[-1] |= count & 0x1F  # 32 is 00000 so we mask the top
            elif instruction[0] == "out":
                #                instr delay dst count
                assembled.append(0b011_00000_000_00000)
                destination = instruction[1]
                try:
                    assembled[-1] |= OUT_DESTINATIONS.index(destination) << 5
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid out destination '{destination}'"
                    ) from exc
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
                if instruction[1].startswith("rxfifo["):  # mov rxfifo[], isr
                    assembled.append(0b100_00000_0001_0_000)
                    if instruction[2] != "isr":
                        raise ValueError("mov rxfifo[] source must be isr")
                    assembled[-1] |= parse_rxfifo_brackets(instruction[1], "txput")
                elif instruction[2].startswith("rxfifo["):  # mov osr, rxfifo[]
                    assembled.append(0b100_00000_1001_0_000)
                    if instruction[1] != "osr":
                        raise ValueError("mov ,rxfifo[] target must be osr")
                    assembled[-1] |= parse_rxfifo_brackets(instruction[2], "txget")
                else:
                    assembled.append(0b101_00000_000_00_000)
                    assembled[-1] |= mov_destinations.index(instruction[1]) << 5
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
                #                instr delay z c w tp/idx
                assembled.append(0b110_00000_0_0_0_00000)

                irq_type = 0
                if instruction[-1] == "prev":
                    irq_type = 1
                    require_version(1, "irq prev")
                    instruction.pop()
                elif instruction[-1] == "next":
                    irq_type = 3
                    require_version(1, "irq next")
                    instruction.pop()
                elif instruction[-1] == "rel":
                    irq_type = 2
                    instruction.pop()

                assembled[-1] |= irq_type << 3

                num = int_in_range(instruction[-1], 0, 8, "irq index")
                assembled[-1] |= num
                instruction.pop()

                if len(instruction) > 1:  # after rel has been removed
                    if instruction[-1] == "wait":
                        assembled[-1] |= 0x20
                    elif instruction[-1] == "clear":
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
                raise RuntimeError(f"Unknown instruction: {instruction[0]}")
            assembled[-1] |= delay << 8
            # print(bin(assembled[-1]))

        self.pio_kwargs = {
            "sideset_enable": sideset_enable,
        }

        if offset != -1:
            self.pio_kwargs["offset"] = offset

        if pio_version != 0:
            self.pio_kwargs["pio_version"] = pio_version

        if sideset_count != 0:
            self.pio_kwargs["sideset_pin_count"] = sideset_count

        if wrap is not None:
            self.pio_kwargs["wrap"] = wrap
        if wrap_target is not None:
            self.pio_kwargs["wrap_target"] = wrap_target

        if fifo_type != "auto":
            self.pio_kwargs["fifo_type"] = fifo_type

        if mov_status_type is not None:
            self.pio_kwargs["mov_status_type"] = mov_status_type
            self.pio_kwargs["mov_status_n"] = mov_status_n

        if set_count is not None:
            self.pio_kwargs["set_pin_count"] = set_count

        if out_count not in (None, 32):
            self.pio_kwargs["out_pin_count"] = out_count

        if out_shift_right is not None:
            self.pio_kwargs["out_shift_right"] = out_shift_right

        if auto_pull is not None:
            self.pio_kwargs["auto_pull"] = auto_pull

        if pull_threshold is not None:
            self.pio_kwargs["pull_threshold"] = pull_threshold

        if in_count not in (None, 32):
            self.pio_kwargs["in_pin_count"] = in_count

        if in_shift_right is not None:
            self.pio_kwargs["in_shift_right"] = in_shift_right

        if auto_push is not None:
            self.pio_kwargs["auto_push"] = auto_push

        if push_threshold is not None:
            self.pio_kwargs["push_threshold"] = push_threshold

        self.assembled = array.array("H", assembled)

        self.debuginfo = (linemap, text_program) if build_debuginfo else None

    def print_c_program(self, name: str, qualifier: str = "const") -> None:
        """Print the program into a C program snippet"""
        if self.debuginfo is None:
            linemap = []
            program_lines = []
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


def assemble(program_text: str) -> MutableSequence[int]:
    """Converts pioasm text to encoded instruction bytes

    In new code, prefer to use the `Program` class so that the extra arguments
    such as the details about side-set pins can be easily passsed to the
    ``StateMachine`` constructor."""
    return Program(program_text).assembled
