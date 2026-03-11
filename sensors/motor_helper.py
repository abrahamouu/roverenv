from gpiozero import PWMOutputDevice, DigitalOutputDevice
from interrupt import STOP_EVENT, MOTOR_LOCK

### if motors too fast lower speed value ###

# LEFT FRONT
lf_enable = PWMOutputDevice(16)
lf_in1 = DigitalOutputDevice(20)
lf_in2 = DigitalOutputDevice(21)

# LEFT BACK
lb_enable = PWMOutputDevice(13)
lb_in1 = DigitalOutputDevice(19)
lb_in2 = DigitalOutputDevice(26)

# RIGHT FRONT
rf_enable = PWMOutputDevice(18)
rf_in1 = DigitalOutputDevice(23)
rf_in2 = DigitalOutputDevice(24)

# RIGHT BACK
rb_enable = PWMOutputDevice(17)
rb_in1 = DigitalOutputDevice(27)
rb_in2 = DigitalOutputDevice(22)

# ---------------- INTERNAL LOW-LEVEL MOTOR WRITES ---------------- #

def _lf_motor(direction, speed):
    if direction == "forward":
        lf_in1.on(); lf_in2.off()
    elif direction == "backward":
        lf_in1.off(); lf_in2.on()
    else:
        lf_in1.off(); lf_in2.off()
    lf_enable.value = speed

def _lb_motor(direction, speed):
    if direction == "backward":
        lb_in1.on(); lb_in2.off()
    elif direction == "forward":
        lb_in1.off(); lb_in2.on()
    else:
        lb_in1.off(); lb_in2.off()
    lb_enable.value = speed

def _rf_motor(direction, speed):
    if direction == "backward":
        rf_in1.on(); rf_in2.off()
    elif direction == "forward":
        rf_in1.off(); rf_in2.on()
    else:
        rf_in1.off(); rf_in2.off()
    rf_enable.value = speed

def _rb_motor(direction, speed):
    if direction == "forward":
        rb_in1.on(); rb_in2.off()
    elif direction == "backward":
        rb_in1.off(); rb_in2.on()
    else:
        rb_in1.off(); rb_in2.off()
    rb_enable.value = speed

# ---------------- SAFETY GUARD ---------------- #

def _guard(fn):
    if STOP_EVENT.is_set():
        return
    with MOTOR_LOCK:
        if STOP_EVENT.is_set():
            return
        fn()

# ---------------- PUBLIC MOVEMENT API ---------------- #

def stop():
    with MOTOR_LOCK:
        _lf_motor("stop", 0)
        _lb_motor("stop", 0)
        _rf_motor("stop", 0)
        _rb_motor("stop", 0)

def forward(speed=1.0):
    _guard(lambda: (
        _lf_motor("forward", speed),
        _lb_motor("forward", speed),
        _rf_motor("forward", speed),
        _rb_motor("forward", speed)
    ))

def backward(speed=1.0):
    _guard(lambda: (
        _lf_motor("backward", speed),
        _lb_motor("backward", speed),
        _rf_motor("backward", speed),
        _rb_motor("backward", speed)
    ))

def turn_left(speed=1.0):
    _guard(lambda: (
        _rf_motor("forward", speed * 0.3),
        _rb_motor("forward", speed * 0.3),
        _lf_motor("backward", speed * 0.3),
        _lb_motor("backward", speed * 0.3)
    ))

def turn_right(speed=1.0):
    _guard(lambda: (
        _lf_motor("forward", speed * 0.3),
        _lb_motor("forward", speed * 0.3),
        _rf_motor("backward", speed * 0.4),
        _rb_motor("backward", speed * 0.4)
    ))
