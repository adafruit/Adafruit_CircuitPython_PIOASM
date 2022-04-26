# SPDX-FileCopyrightText: Copyright (c) 2021 Scott Shawcroft for Adafruit Industries LLC
# SPDX-FileCopyrightText: Copyright (c) 2022 Jeff Epler for Adafruit Industries LLC
#
# SPDX-License-Identifier: MIT
"""
`adafruit_pioasm`
================================================================================

Simple assembler to convert pioasm to bytes


* Author(s): Scott Shawcroft, Jeff Epler
"""
import array
import collections
import sys

try:
    import re
except ImportError:
    import ure as re

re_type = type(re.compile(""))

MatchResult = collections.namedtuple("MatchResult", ["needle", "match"])

if hasattr(re, "DOTALL"):
    star_dotall = (re.DOTALL,)
else:
    star_dotall = ()


class NamedRE:
    """A Regular Expression that has a useful repr()"""

    def __init__(self, name, pattern):
        self._name = name
        self.match = re.compile(pattern).match

    def __str__(self):
        """Return the RE's name"""
        return self._name

    def __repr__(self):
        """Return the RE's repr"""
        return f"<{self._name}>"


# Indices must match instruction values! Trailing reserved values may be omitted,
# internal reserved values must be None
SetDestinations = ["pins", "x", "y", None, "pindirs"]
WaitSources = ["gpio", "pin", "irq"]
InSources = ["pins", "x", "y", "null", None, None, "isr", "osr"]
OutDestinations = ["pins", "x", "y", "null", "pindirs", "pc", "isr", "exec"]
MovDestinations = ["pins", "x", "y", None, "exec", "pc", "isr", "osr"]
MovSources = ["pins", "x", "y", "null", None, "status", "isr", "osr"]
JmpConditions = [None, "!x", "x--", "!y", "y--", "x!=y", "pin", "!osre"]

wait_source_max = {"gpio": 32, "pin": 32, "irq": 8}

Number = NamedRE("Number", r"[1-9][0-9]*|0o?[0-7]+|0x[0-9a-fA-F]+|0b[01]+|0")
Identifier = NamedRE("Identifier", r"[A-Za-z_][A-Za-z_0-9]*")
Label = NamedRE("Label", r"[A-Za-z_][A-Za-z_0-9]*:")
Pseudo = NamedRE("Pseudo-Op", r"\.[A-Za-z_][A-Za-z_0-9]*")
ws = NamedRE("Whitespace", r"[ \t]+")
ws_comma = NamedRE("Optional comma and whitespace", r"[ \t]*,[ \t]*|[ \t]+")
comment_nl = NamedRE("Comment", r";[^\n]*\n")
comment = NamedRE("Comment", r";[^\n]*")
Instruction = NamedRE("Instruction", r"nop|jmp|wait|in|out|push|pull|mov|irq|set")


def _to_int(val):
    val = _match_value(val)
    if len(val) > 1 and val[0] == "0" and val[1] in "01234567":
        return int(val, 8)
    return int(val, 0)


def _match_value(obj):
    """Get the value of a parsed object (which can be a str or a match-like object)"""
    if obj is None:
        return None
    match = obj.match
    if isinstance(match, str):
        return match
    return match.group(0)


def match_len(obj):
    """Get the length of a parsed object (which can be a str or a match-like object)"""
    match = obj.match
    if isinstance(match, str):
        return len(match)
    return match.end() - match.start()


class ParseError(SyntaxError):
    """This error is raised when pio source cannot be parsed"""


class _Parser:  # pylint: disable=too-few-public-methods
    """Base class for recursive-descent parsing"""

    def __init__(self, data) -> None:
        if not data.endswith("\n"):
            data += "\n"
        self._data = data
        self._pos = 0
        self._parse()  # pylint: disable=no-member
        if not self._eof():
            self._parse_error("Not all data parsed")

    def _match_next(self, needle):
        """Check whether needle matches next"""
        if needle is None:
            return None
        if isinstance(needle, str):
            if self._data.startswith(needle, self._pos):
                return MatchResult(needle, needle)
        else:
            match = needle.match(self._data, self._pos)
            if match is not None:
                return MatchResult(needle, match)
        return None

    def _one_of_next(self, *args, ignore=None):
        """Check whether one of the options appears next. Never advances the parse position"""
        pos = self._pos
        try:
            return self._one_of(*args, ignore=ignore)
        finally:
            self._pos = pos

    def _one_of(self, *args, ignore=None):
        if ignore:
            while self._one_of(ignore):
                pass

        for needle in args:
            if result := self._match_next(needle):
                self._pos += match_len(result)
                return result

        return None

    def _ignore_one_of(self, *args):
        while self._one_of(*args):
            pass

    def _lineno(self, pos=None):
        if pos is None:
            pos = self._pos
        return self._data.count("\n", 0, pos)

    def _start_of_line(self, pos=None):
        if pos is None:
            pos = self._pos
        try:
            return self._data.rindex("\n", 0, pos) + 1
        except ValueError:
            return 0

    def _end_of_line(self, pos=None):
        if pos is None:
            pos = self._pos
        try:
            return self._data.index("\n", pos)
        except ValueError:
            return len(self._data)

    def _parse_error(self, info, pos=None):
        if pos is None:
            pos = self._pos
        lineno = self._lineno(pos)
        start_of_line = self._start_of_line(pos)
        end_of_line = self._end_of_line(pos)
        column = 1 + pos - start_of_line
        line = self._data[start_of_line:end_of_line]
        raise ParseError(
            f"Line {lineno}, column {column}: {info}\n    {line.rstrip()}\n    {'^':>{column}}\n"
        )

    def _parse_one_of(self, *args, ignore=None, msg=None):
        if result := self._one_of(*args, ignore=ignore):
            return result

        return self._parse_error(msg or f"Expected {', '.join(repr(a) for a in args)}")

    def _eof(self):
        return self._pos == len(self._data)


class Program(_Parser):
    """Encapsulates a program's instruction stream and configuration flags

    Example::

        program = adafruit_pioasm.Program(...)
        state_machine = rp2pio.StateMachine(program.assembled, ..., **program.pio_kwargs)

    """

    def __init__(self, data, build_debuginfo=False):
        self.linemap = []
        self.assembled = array.array("H")
        self.fixups = {}
        self.labels = {}
        self.side_set_count = 0
        self.side_set_opt = None
        self.program_name = None
        self.pio_kwargs = {}
        super().__init__(data)
        for target, (label, pos) in self.fixups.items():
            offset = self.labels.get(label, None)
            if offset is None:
                self._parse_error(f"Jump to undefined label {label}", pos=pos)
            self.assembled[target] |= offset
        if self.side_set_count != 0:
            self.pio_kwargs["sideset_pin_count"] = self.side_set_count
        self.pio_kwargs["sideset_enable"] = bool(self.side_set_opt)
        if (wrap_target := self.labels.get(".wrap_target")) is not None:
            self.pio_kwargs["wrap_target"] = wrap_target
        if (wrap := self.labels.get(".wrap")) is not None:
            self.pio_kwargs["wrap"] = wrap
        if build_debuginfo:
            self.debuginfo = (self.linemap, data)
        else:
            self.debuginfo = None
        del self.linemap

    def _parse(self):
        while not self._eof():
            while self._one_of("\n", comment_nl, ignore=ws):
                self.linemap.append(len(self.assembled))
            if self._eof():
                break
            self._parse_instruction()
            self.linemap.append(len(self.assembled))
            self._parse_one_of("\n", ignore=comment)

    def _parse_instruction(self):
        oper = self._parse_one_of(Pseudo, Label, Instruction, ignore=ws)

        val = _match_value(oper)
        if oper[0] is Instruction:
            instr = getattr(self, "_instruction_" + val, self._unknown_instruction)(
                oper
            )
            instr |= self._parse_delay_side_set()
            self.assembled.append(instr)
        elif oper[0] is Pseudo:
            getattr(self, "_pseudo_" + val[1:], self._unknown_pseudo)(oper)
        elif oper[0] is Label:
            self._define_label(val[:-1])

    def _parse_delay_side_set(self):
        side = None
        max_side = 2**self.side_set_count
        delay_bits = 5 - self.side_set_count - (self.side_set_opt or 0)
        max_delay = 2**delay_bits
        dss = 0
        if self._one_of("side", ignore=ws_comma):
            side = self._parse_expression("Side-set value", 0, max_side)
        if self._one_of("[", ignore=ws_comma):
            dss = self._parse_expression("Side-set value", 0, max_delay)
            self._parse_one_of("]", ignore=ws)
        if side is not None:
            dss |= side << (delay_bits)
            if self.side_set_opt:
                dss |= 0x10
        return dss << 8

    def _unknown_instruction(self, oper):
        self._parse_error(f"Unhandled instruction {_match_value(oper)}")

    def _unknown_pseudo(self, oper):
        self._parse_error(f"Unhandled pseudo-instruction {_match_value(oper)}")

    def _define_label(self, name, value=None):
        if name in self.labels:
            self._parse_error(f"Duplicate label {name}")
        if value is None:
            value = len(self.assembled)
        self.labels[name] = value

    def _parse_expression(self, what=None, min_=None, max_=None):
        self._ignore_one_of(ws)
        startpos = self._pos
        val = self._parse_one_of(Number)
        result = _to_int(val)
        if min_ is not None:
            if result < min_:
                self._parse_error(
                    f"{what or 'Value'} {result} must be >= {min_}", startpos
                )
        if max_ is not None:
            if result >= max_:
                self._parse_error(
                    f"{what or 'Value'} {result} must be < {max_}", startpos
                )
        return result

    def _pseudo_program(self, _):
        if self.program_name is not None:
            self._parse_error("Multiple programs not supported")
        self.program_name = self._parse_one_of(Identifier, ignore=ws)

    def _pseudo_wrap(self, _):
        if len(self.assembled) == 0:
            self._parse_error("Cannot have .wrap as first instruction")
        self._define_label(".wrap", len(self.assembled) - 1)

    def _pseudo_wrap_target(self, _):
        self._define_label(".wrap_target")

    def _pseudo_side_set(self, _):
        if self.side_set_opt is not None:
            self._parse_error("Multiple .side_set not permitted")
        self.side_set_count = self._parse_expression("Number of side set pins", 0, 6)
        self.side_set_opt = bool(self._one_of("opt", ignore=ws))

    def _instruction_nop(self, _):  # pylint: disable=no-self-use
        #                          mov delay   y oper   y
        return 0b101_00000_010_00_010

    def _instruction_pull(self, _):
        #        instr delay d i b zero
        instr = 0b100_00000_1_0_0_00000
        if self._one_of("block", ignore=ws):
            self._one_of(ignore=ws_comma)
            instr |= 0x20
        if self._one_of("ifempty", ignore=ws):
            instr |= 0x40
        return instr

    def _instruction_push(self, _):
        #        instr delay d i b zero
        instr = 0b100_00000_0_0_0_00000
        if self._one_of("block", ignore=ws):
            self._one_of(ignore=ws_comma)
            instr |= 0x20
        if self._one_of("iffull", ignore=ws):
            instr |= 0x40
        return instr

    def _instruction_jmp(self, _):
        instr = 0b000_00000_000_00000
        condition = _match_value(self._one_of(*JmpConditions, ignore=ws))
        if condition is not None:
            instr |= JmpConditions.index(condition) << 5
            self._ignore_one_of(ws_comma)
        if self._one_of_next(Number):
            target = self._parse_expression("jmp target", 0, 32)
            instr |= target
        else:
            pos = self._pos
            target = self._parse_one_of(Identifier, ignore=ws)
            self.fixups[len(self.assembled)] = _match_value(target), pos
        return instr

    def _instruction_set(self, _):
        #       instr delay dst data
        instr = 0b111_00000_000_00000
        dest = self._parse_one_of(
            *SetDestinations, ignore=ws, msg="Invalid set destination"
        )
        instr |= SetDestinations.index(_match_value(dest)) << 5
        self._ignore_one_of(ws_comma)
        val = self._parse_expression("Set value", 0, 32)
        instr |= val
        return instr

    def _instruction_wait(self, _):
        #       instr delay p sr index
        instr = 0b001_00000_0_00_00000
        polarity = self._parse_expression("Polarity", 0, 2)
        source = _match_value(self._parse_one_of(*WaitSources, ignore=ws_comma))
        self._ignore_one_of(ws_comma)
        index = self._parse_expression(f"{source} number", 0, wait_source_max[source])
        if source == "irq":
            if self._one_of("rel", ignore=ws):
                index |= 0x10
        instr |= polarity << 7
        instr |= WaitSources.index(source) << 5
        instr |= index

        return instr

    def _instruction_in(self, _):
        #       instr delay src count
        instr = 0b010_00000_000_00000
        source = _match_value(self._parse_one_of(*InSources, ignore=ws))
        count = self._parse_expression("In count", 1, 33)
        instr |= InSources.index(source) << 5
        instr |= count & 0x1F  # encode 32 as 0

    def _instruction_out(self, _):
        #       instr delay src count
        instr = 0b011_00000_000_00000
        dest = _match_value(self._parse_one_of(*OutDestinations, ignore=ws))
        count = self._parse_expression("Out count", 1, 33)
        instr |= OutDestinations.index(dest) << 5
        instr |= count & 0x1F  # encode 32 as 0
        return instr

    def _instruction_mov(self, _):
        #       instr delay dst oper src
        instr = 0b101_00000_000_00_000
        dest = _match_value(self._parse_one_of(*MovDestinations, ignore=ws))
        instr |= MovDestinations.index(dest) << 5
        self._ignore_one_of(ws_comma)
        opt = _match_value(self._one_of("~", "!", "::"))
        src = self._parse_one_of(*MovSources, ignore=ws, msg="Invalid mov source")
        if opt in "~!":
            instr |= 0b01 << 3
        elif opt == "::":
            instr |= 0b10 << 3
        instr |= MovSources.index(_match_value(src))
        return instr

    def _instruction_irq(self, _):
        #       instr delay 0 c w index
        instr = 0b110_00000_0_0_0_00000

        modifier = _match_value(self._one_of("set", "nowait", "wait", "clear"))
        # "set" and "nowait" modifiers are the same as the default, c=w=0
        # c=w=1 is reserved/invalid
        if modifier == "wait":
            instr |= 0x20
        if modifier == "clear":
            instr |= 0x40

        index = self._parse_expression("IRQ number", 0, 8)
        instr |= index

        if self._one_of("rel"):
            instr |= 0x10

        return instr

    def print_c_program(self, name, qualifier="const", file=None):
        """Print the program into a C program snippet"""
        if file is None:
            file = sys.stdout

        print(
            f"{qualifier} int {name}_wrap = {self.pio_kwargs.get('wrap', len(self.assembled)-1)};",
            file=file,
        )
        print(
            f"{qualifier} int {name}_wrap_target = {self.pio_kwargs.get('wrap_target', 0)};",
            file=file,
        )
        sideset_pin_count = self.pio_kwargs.get("sideset_pin_count", 0)
        print(
            f"{qualifier} int {name}_sideset_pin_count = {sideset_pin_count};",
            file=file,
        )
        print(
            f"{qualifier} bool {name}_sideset_enable = {self.pio_kwargs['sideset_enable']};",
            file=file,
        )
        print(f"{qualifier} uint16_t {name}[] = " + "{", file=file)
        if self.debuginfo:
            linemap = iter(self.debuginfo[0])
            program_lines = iter(self.debuginfo[1].split("\n"))
            for i, inst in enumerate(self.assembled):
                while next(linemap) <= i:
                    line = next(program_lines)
                    if line:
                        print(f"            // {line}", file=file)
                print(f"    0x{inst:04x}, // {next(program_lines)}", file=file)
            for line in program_lines:
                print(f"            // {line}", file=file)
        else:
            for i in range(0, len(self.assembled), 8):
                print(
                    "    " + ", ".join("0x%04x" % i for i in self.assembled[i : i + 8]),
                    file=file,
                )
        print("};", file=file)
        print(file=file)


def assemble(program_text: str) -> array.array:
    """Converts pioasm text to encoded instruction bytes

    In new code, prefer to use the `Program` class so that the extra arguments
    such as the details about side-set pins can be easily passsed to the
    ``StateMachine`` constructor."""
    return Program(program_text).assembled
