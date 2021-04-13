'''
written by Parsko Apr 12, 2021

This is an example of how to use the PIO for a button.
This code is derived from the encoder code.

Connect a button between a ground (GND) pin and D4.
Edit the pin (~line 73) as needed for your own use.

If you open the serial REPL it prints...
'i' is the button state, which times out and counts
up.  Used to check for bouncing.  Mine didn't seem to bounce,
or my code was bad?
'button_d4:' is the switch value, without timing out.
'time:' is the time elapsed since last button pressed, used
for checking bouncing.

I won't know for sure if the bouncing works or not
until I have it connected to something like a motor drive.

'''
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

        self._buffer = bytearray(1)


    def deinit(self):
        self._sm.deinit()

    @property
    def value(self):
        while self._sm.in_waiting:
            self._sm.readinto(self._buffer)
        return self._buffer[0]


if __name__ == "__main__":
    try:

        button_d4 = button(board.D4)
        i = 0
        start_time = time.monotonic_ns()
        press_time = start_time
        previous_value = button_d4.value
        while True:
            value = button_d4.value

            print('i: ',i,"  button_d4:", value, 'time:',start_time-press_time)
            time.sleep(0.1)

            if previous_value != value and value == 0:
                i += 1
                press_time = time.monotonic_ns()

            if previous_value != value and value == 1:
                i = press_time = 0

            if start_time - press_time > 1000000000:
                i = 0

            start_time = time.monotonic_ns()
            previous_value = value

    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        print('Keyboard Interupt, ending routine')
    finally:
        button_d4.deinit()
