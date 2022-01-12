# SPDX-FileCopyrightText: 2021 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# pylint: disable=missing-module-docstring,invalid-name,missing-function-docstring,missing-class-docstring

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).absolute().parent.parent))

import adafruit_pioasm  # pylint: disable=wrong-import-position


def nice_opcode(o):
    o = f"{o:016b}"
    return o[:3] + "_" + o[3:8] + "_" + o[8:]


class AssembleChecks(unittest.TestCase):
    def assertAssemblesTo(self, source, expected):
        actual = adafruit_pioasm.assemble(source)
        expected_bin = [nice_opcode(x) for x in expected]
        actual_bin = [nice_opcode(x) for x in actual]
        self.assertEqual(
            expected_bin,
            actual_bin,
            f"Assembling {source!r}: Expected {expected_bin}, got {actual_bin}",
        )

    def assertAssemblyFails(self, source, match=None, errtype=RuntimeError):
        if match:
            self.assertRaisesRegex(errtype, match, adafruit_pioasm.assemble, source)
        else:
            self.assertRaises(errtype, adafruit_pioasm.assemble, source)

    def assertPioKwargs(self, source, **kw):
        program = adafruit_pioasm.Program(source)
        self.assertEqual(kw, program.pio_kwargs)


class TestNop(AssembleChecks):
    def testNonsense(self):
        self.assertAssemblyFails("nope")

    def testNop(self):
        self.assertAssemblesTo("nop", [0b101_00000_010_00_010])
        self.assertAssemblesTo(
            "nop\nnop", [0b101_00000_010_00_010, 0b101_00000_010_00_010]
        )
        self.assertAssemblesTo("nop [1]", [0b101_00001_010_00_010])
        self.assertAssemblesTo("nop [31]", [0b101_11111_010_00_010])
        self.assertAssemblesTo(".side_set 1\nnop side 1", [0b101_10000_010_00_010])
        self.assertAssemblesTo(".side_set 1\nnop side 1 [15]", [0b101_11111_010_00_010])

    def testSidesetOpt(self):
        self.assertAssemblesTo(".side_set 1 opt\nnop side 1", [0b101_11000_010_00_010])
        self.assertAssemblesTo(".side_set 1 opt\nnop side 0", [0b101_10000_010_00_010])
        self.assertAssemblesTo(
            ".side_set 1 opt\nnop side 0 [1]", [0b101_10001_010_00_010]
        )
        self.assertAssemblesTo(".side_set 1 opt\nnop [1]", [0b101_00001_010_00_010])
        self.assertAssemblesTo(".side_set 1 opt\nnop [7]", [0b101_00111_010_00_010])
        self.assertAssemblesTo(
            ".side_set 1 opt\nnop side 1 [1]", [0b101_11001_010_00_010]
        )
        self.assertAssemblesTo(
            ".side_set 1 opt\nnop side 0 [7]", [0b101_10111_010_00_010]
        )

    def testSet(self):
        # non happy path
        self.assertAssemblyFails(
            "set isr, 1", match="Invalid set destination 'isr'", errtype=ValueError
        )

    def testJmp(self):
        self.assertAssemblesTo("l:\njmp l", [0b000_00000_000_00000])
        self.assertAssemblesTo("l:\njmp 7", [0b000_00000_000_00111])
        self.assertAssemblesTo("jmp l\nl:", [0b000_00000_000_00001])
        self.assertAssemblesTo("jmp !x, l\nl:", [0b000_00000_001_00001])
        self.assertAssemblesTo("jmp x--, l\nl:", [0b000_00000_010_00001])
        self.assertAssemblesTo("jmp !y, l\nl:", [0b000_00000_011_00001])
        self.assertAssemblesTo("jmp y--, l\nl:", [0b000_00000_100_00001])
        self.assertAssemblesTo("jmp x!=y, l\nl:", [0b000_00000_101_00001])
        self.assertAssemblesTo("jmp pin, l\nl:", [0b000_00000_110_00001])
        self.assertAssemblesTo("jmp !osre, l\nl:", [0b000_00000_111_00001])
        # non happy path
        self.assertAssemblyFails(
            "jmp x--., l\nl:", match="Invalid jmp condition 'x--.'", errtype=ValueError
        )

    def testWait(self):
        self.assertAssemblesTo("wait 0 gpio 0", [0b001_00000_0_00_00000])
        self.assertAssemblesTo("wait 0 gpio 1", [0b001_00000_0_00_00001])
        self.assertAssemblesTo("wait 1 gpio 2", [0b001_00000_1_00_00010])
        self.assertAssemblesTo("wait 0 pin 0", [0b001_00000_0_01_00000])
        self.assertAssemblesTo("wait 0 pin 1", [0b001_00000_0_01_00001])
        self.assertAssemblesTo("wait 1 pin 2", [0b001_00000_1_01_00010])
        self.assertAssemblesTo("wait 0 irq 0", [0b001_00000_0_10_00000])
        self.assertAssemblesTo("wait 0 irq 0 rel", [0b001_00000_0_10_10000])
        self.assertAssemblesTo("wait 1 irq 0", [0b001_00000_1_10_00000])
        self.assertAssemblesTo("wait 0 irq 1 rel", [0b001_00000_0_10_10001])

    def testLimits(self):
        self.assertAssemblyFails(".side_set 1\nnop side 2")
        self.assertAssemblyFails(".side_set 1\nnop side 2 [1]")
        self.assertAssemblyFails("nop [32]")
        self.assertAssemblyFails(".side_set 1\nnop side 0 [16]")
        self.assertAssemblyFails(".side_set 1 opt\nnop side 0 [8]")

    def testCls(self):
        self.assertPioKwargs("", sideset_count=0, sideset_enable=False)
        self.assertPioKwargs(".side_set 1", sideset_count=1, sideset_enable=False)
        self.assertPioKwargs(".side_set 3 opt", sideset_count=3, sideset_enable=True)


class TestMov(AssembleChecks):
    def testMovNonHappy(self):
        # non happy path
        self.assertAssemblyFails(
            "mov x, blah", match="Invalid mov source 'blah'", errtype=ValueError
        )

    def testMovInvert(self):
        # test moving and inverting
        self.assertAssemblesTo("mov x, ~ x", [0b101_00000_001_01_001])
        self.assertAssemblesTo("mov x, ~ x", [0b101_00000_001_01_001])
        self.assertAssemblesTo("mov x, ~x", [0b101_00000_001_01_001])
        self.assertAssemblesTo("mov x, !x", [0b101_00000_001_01_001])

    def testMovReverse(self):
        # test moving and reversing bits
        self.assertAssemblesTo("mov x, :: x", [0b101_00000_001_10_001])
        self.assertAssemblesTo("mov x, ::x", [0b101_00000_001_10_001])
