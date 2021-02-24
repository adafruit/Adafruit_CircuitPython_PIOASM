# SPDX-FileCopyrightText: 2021 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Adapted from the example https://github.com/raspberrypi/pico-examples/tree/master/pio/hello_pio

import adafruit_pioasm
import board
import rp2pio
import time

hello = """
.program hello
loop:
    pull
    out pins, 1
    jmp loop
"""

assembled = adafruit_pioasm.assemble(hello)

sm = rp2pio.StateMachine(
    assembled,
    frequency=80,
    init=adafruit_pioasm.assemble("set pindirs 1"),
    first_set_pin=board.LED,
    first_out_pin=board.LED,
)
print("real frequency", sm.frequency)

while True:
    sm.write(bytes((1,)))
    time.sleep(0.5)
    sm.write(bytes((0,)))
    time.sleep(0.5)
