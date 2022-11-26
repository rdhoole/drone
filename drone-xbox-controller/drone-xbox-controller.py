from __future__ import print_function
import xbox

import socket
from time import sleep
import threading
from sys import exit

# Format floating point number to string format -x.xxx
def fmtFloat(n):
    return '{:0.4f}'.format(n)

# Print one or more values without a line feed
def show(*args):
    for arg in args:
        print(arg, end="")

# Print true or false value based on a boolean, without linefeed
def showIf(boolean, ifTrue, ifFalse=" "):
    if boolean:
        show(ifTrue)
    else:
        show(ifFalse)

def _print(str):
    print(":" + str)

def clean_up():
    global s
    s.close()
    exit(0)
    
def user_exit():
    global joy
    _print("Are you sure?")
    _print("A for Yes, B for No")
    while not joy.A() or not joy.B():
        if (joy.A()):
            _print("Ok, bye!")
            clean_up()
        if (joy.B()):
            _print("Ok, welcome back!")
            break
        sleep(0.01)
    
def connect():
    global s
    global connected
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("192.168.2.1", 12122))
        _print("Connected.")
        return True
    except:
        _print("Failed to connect")
        return False

def disconnect():
    global s
    global connected
    try:
        s.close()
        _print("Disconnected.")
        return False
    except:
        pass

throttle_trim_amount = 0.0001
throttle_trim_up = 0
throttle_trim_down = 0
throttle = 0.0
t = 0

def trim(t):
    global throttle
    global throttle_trim_up
    global throttle_trim_down

    if t <= 1.0 and t >= 0.0:
        throttle = t
        if t > 0.5:
            throttle_trim_up = 0.5 + (0.5 - t)
            throttle_trim_down = 0.5 + (t - 0.5)
        if t < 0.5:
            throttle_trim_up = 0.5 - (t - 0.5)
            throttle_trim_down = 0.5 - (0.5 - t)
        if t == 0.5:
            throttle_trim_up = throttle_trim_down = t
    
# Instantiate the controller
joy = xbox.Joystick()
running = True
connected = False
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Show various axis and button states until Back button is pressed
_print("Xbox controller for drone!")
_print("Press Start to connect to drone controller, and Back to close.")
_print("Press Start and Back to exit.")
_print("Adjust trim to activate throttle.")
_print("Have fun!")

while running:
    # exit
    if joy.Start() and joy.Back():
        user_exit()
    
    if joy.Start() and not connected:
        connected = connect()

    if joy.Back() and connected:
        connected = disconnect()

    if joy.rightBumper():
        trim(throttle + throttle_trim_amount)

    if joy.leftBumper():
        trim(throttle - throttle_trim_amount)
        
    # send commands to drone controller
    if connected:
        # pitch, roll, yaw, throttle
        pitch = fmtFloat(joy.leftY())
        roll  = fmtFloat(joy.leftX())
        yaw   = fmtFloat(joy.rightX())
        t     = fmtFloat((joy.rightTrigger() * throttle_trim_up) - \
                         (joy.leftTrigger() * throttle_trim_down) + throttle)

        data = '{0} {1} {2} {3}\n'.format(pitch, roll, yaw, t)
        try:
            s.send(data.encode())
        except:
            _print("Lost connection!")
            connected = disconnect()
            
    sleep(0.01) # base this off some value?
        
# Close out when done
joy.close()
