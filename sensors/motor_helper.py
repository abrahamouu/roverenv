from gpiozero import PWMOutputDevice, DigitalOutputDevice
### if motors to fast lower speed value ### 

# right motors (front) moving opposite for some reason, fix next time.

# differential steering, one motor driver for left motors and one for right motors
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

# -------------------------- Motor Defintions ---------------------------------- #

def lf_motor(direction, speed = 1.0):
    if direction == "forward":
        lf_in1.on()
        lf_in2.off()  # L298N specific, moves both left motors forward
    elif direction == "backward":
        lf_in1.off()
        lf_in2.on()  
    else:   # coasting, if want sudden brake change to on() for both
        lf_in1.off()
        lf_in2.off()
    
    lf_enable.value = speed

def lb_motor(direction, speed = 1.0):
    if direction == "backward":
        lb_in1.on()
        lb_in2.off() 
    elif direction == "forward":
        lb_in1.off()
        lb_in2.on()  
    else:
        lb_in1.off()
        lb_in2.off()
        
    lb_enable.value = speed

def rf_motor(direction, speed = 1.0):
    if direction == "backward":
        rf_in1.on()
        rf_in2.off()  # L298N specific, moves both left motors forward
    elif direction == "forward":
        rf_in1.off()
        rf_in2.on()
    else:   # coasting, if want sudden brake change to on() for both
        rf_in1.off()
        rf_in2.off()
    
    rf_enable.value = speed

def rb_motor(direction, speed = 1.0):
    if direction == "forward":
        rb_in1.on()
        rb_in2.off() 
    elif direction == "backward":
        rb_in1.off()
        rb_in2.on()  
    else:
        rb_in1.off()
        rb_in2.off()
    
    rb_enable.value = speed

# ------------------------- Movement Functions ---------------------------- # 
def stop():
    lf_motor("stop", 0)
    lb_motor("stop", 0)
    rf_motor("stop", 0)
    rb_motor("stop", 0)

# change speed of motors here
def forward(speed = 1.0):
    lf_motor("forward", speed)
    lb_motor("forward", speed)
    rf_motor("forward", speed)
    rb_motor("forward", speed)

def backward(speed = 1.0):
    lf_motor("backward", speed)
    lb_motor("backward", speed)
    rf_motor("backward", speed)
    rb_motor("backward", speed)
    
# smooth turn, might change based on implementation
def turn_left(speed = 1.0):
    rf_motor("forward", speed)
    rb_motor("forward", speed)
    # lf_motor("backward", speed * 0.2)
    # lb_motor("backward", speed * 0.2)


def turn_right(speed = 1.0):
    lf_motor("forward", speed)
    lb_motor("forward", speed)
    # rf_motor("backward", speed * 0.2)
    # rb_motor("backward", speed * 0.2)
# for more fine-tuned navgation, might not need this
    def steer(speed_left, speed_right):
        if speed_left > 0:
            lf_motor("forward", speed_left)
        elif speed_left < 0:
            lf_motor("backward", speed_left)
        else:
            lf_motor("stop", 0)
        
        if speed_right > 0:
            lb_motor("forward", speed_right)
        elif speed_right < 0:
            lb_motor("backward", speed_right)
        else:
            lb_motor("stop", 0)

