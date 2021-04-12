import adafruit_pioasm
import board
import rp2pio
import array
import digitalio
import time


class button:
    _sm_code = adafruit_pioasm.assemble(
        """
    again:
        in pins, 1
        mov x, isr
        jmp x!=y, push_data
        mov isr, null
        jmp again
    push_data:
        push
        mov y, x
    """
    )

    _sm_init = adafruit_pioasm.assemble("set y 31") # I am not sure what this does.

    def __init__(self, pin_a):
        self._sm = rp2pio.StateMachine(
            self._sm_code,
            2000,
            init=self._sm_init,
            first_in_pin=pin_a,
            in_pin_count=1,
            pull_in_pin_up=0b1,
            in_shift_right=False,
        )

        self._counter = 0
        self._direction = 0
        self._lut_index = 0
        self._buffer = bytearray(1)


    def deinit(self):
        self._sm.deinit()

    @property
    def value(self):
        while self._sm.in_waiting:
            self._sm.readinto(self._buffer)
            #self._update_state_machine(self._buffer[0])
        return self._buffer[0]


button_d4 = button(board.D4)

old_value = None
while True:
    value = button_d4.value
    if old_value != value:
        print("Encoder:", value)
        time.sleep(0.01)
