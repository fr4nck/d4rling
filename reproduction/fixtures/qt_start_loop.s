.text
.globl _start
_start:
    call _qt_probe
L_wait:
    jmp L_wait
