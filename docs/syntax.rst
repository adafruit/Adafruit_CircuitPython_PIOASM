This chapter documents the language features accepted by the `adafruit_pioasm`
assembler. The dialect is intended to be a compatible subset of the one in the
pico-sdk's ``pioasm`` program (which does not produce CircuitPython-compatible
output).

For full details, refer to the relevant chapter in the RP2040 or RP2350 datasheet.

In this informal grammar, ``<angle brackets>`` represent some text, usually a single
word or number. ``{curly brackets}`` represent an element that is optional.
``|`` represents alternatives. ``...`` indicates further arguments that are
explained in the official datasheet.

Lines
~~~~~

First, any portion of the line starting with the comment character ``;`` is removed.
Then, extra whitespace is removed and the line is parsed.

Each line may be:
 * blank
 * a directive
 * a label
 * an instruction, possibly with side-set and delay information

Directives
----------

 * ``.program <identifier>``: Accepts a program name, which should be a valid Python identifier
 * ``.pio_version <number>``: The numeric version of the PIO peripheral to target. Version 0, the default, is in the RP2040. Version 1 is in RP2350
 * ``.origin <number>``: The required load address of the program. If specified and not ``-1``, this will be stored in ``pio_kwargs["offset"]``
 * ``.wrap``, ``.wrap_target``: This pair of directives set the range of instructions for implicit looping, by placing values in ``pio_kwargs``
 * ``.side_set <number> {opt}``: Controls the side-set behavior and sets ``pio_kwargs["sideset_enable"]`` and ``pio_kwargs["sideset_pin_count"]``
 * ``.fifo <identifier>``: Sets the FIFO mode. As a CircuitPython extension, ``auto`` (the default) automatically chooses among ``txrx``, ``tx``, and ``rx`` modes
 * ``.mov_status ...``: Controls what information the ``mov status`` instruction accesses, by placing values in ``pio_kwargs``
 * ``.out <count> {{left|right}} {{auto}}``: Settings that control how the ``out`` instruction works, including shift direction and whether auto pull is enabled, by placing values in ``pio_kwargs``
 * ``.in <count> {{left|right}} {{auto}}``: Settings that control how the ``in`` instruction works, including shift direction and whether auto push is enabled, by placing values in ``pio_kwargs``
 * ``.set <count>``: Settings that control how the ``set`` instruction works, including shift direction and whether auto push is enabled, by placing values in ``pio_kwargs``

Labels
------

 * ``<identifier>:`` creates a label which may be referred to by a ``jmp`` instruction.

Instructions
------------

 * ``nop``
 * ``jmp <number|name>``
 * ``wait ...``
 * ``in ...``
 * ``out ...``
 * ``push ...``
 * ``pull ...``
 * ``mov ...``
 * ``mov rxfifo[y|number], isr`` (requires PIO version 1 and compatible ``.fifo`` setting)
 * ``mov osr, rxfifo[y|number]`` (requires PIO version 1 and compatible ``.fifo`` setting)
 * ``irq <number> {rel}``
 * ``irq next|prev <number>``. (requires PIO version 1) adafruit_pioasm follows sdk pioasm in placing ``next`` and ``prev`` before the IRQ number. The datasheet (version 05c4754) implies a different syntax.
 * ``set ...``

Side-set and delay
------------------
The next part of each line can contain "side-set" and "delay" information, in order.

 * ``side <number>``: Set the side-set pins to ``number``
 * ``[<number>]``: Add ``number`` extra delay cycles to this instruction

The range of these numbers depends on the count of side-set pins and whether side-set is
optional. If side-set is not optional, a missing ``side <number>`` is treated the same as
``side 0``.

Unsupported Features
--------------------

In places where a numeric value is needed, only a valid Python numeric literal
is accepted. Arithmetic is not supported.

Whitespace is not accepted in certain places, for instance within an instruction delay.
It must be written ``[7]`` not ``[ 7 ]``.

Extra commas that would not be acceptable to sdk pioasm are not always diagnosed.

Extra words in some locations that would not be acceptable to sdk pioasm are not always diagnosed.

CircuitPython extensions
------------------------

* ``.fifo auto``: By default, CircuitPython joins the TX and RX fifos if a PIO program only receives or transmits. The ``.fifo auto`` directive makes this explicit.
