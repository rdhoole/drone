#!/usr/bin/env python
# Ryan Hoole

from board import SCL_1, SDA_1
from busio import I2C
from adafruit_pca9685 import PCA9685
from adafruit_servokit import ServoKit
from socket import socket, AF_INET, SOCK_STREAM
import sys
import time
from datetime import datetime


i2c = I2C(SCL_1, SDA_1)
pwm = PCA9685(i2c)
motor = ServoKit(channels=8, i2c=i2c)

pwm.frequency = 50

# settings for Pan tilt servos (camera)
motor.servo[4].set_pulse_width_range(500,2500)
motor.servo[5].set_pulse_width_range(500,2560)
##############################################

def zero_motors():
    global motor
    # zero out motors!
    for i in range(4):
        motor.servo[i].angle = 0

telemetry = None
telemetry_connected = False
def connect_to_telemetry():
    global telemetry
    try:
        telemetry = socket(AF_INET, SOCK_STREAM)
        telemetry.connect(("192.168.2.1", 12121))
        return True
    except Exception as e:
        print(e)
        return False

def disconnect():
    global telemetry
    global telemetry_connected
    if telemetry_connected:
        telemetry.close()

def stabilize_motors(motor, throttle, roll, pitch, yaw, drone_roll, drone_pitch, drone_yaw):
    motor_1, motor_2, motor_3, motor_4 = motor

    # adjust the amount of speed of the motor depending on what the pilot wants compared to drones actual movement
    # if pilot does not intend to move... stabilize
    if pitch == 0.0 and drone_pitch > 0.0 and drone_pitch < 90.0:
        motor_1 += (drone_pitch/2)
        motor_4 += (drone_pitch/2)
    elif pitch == 0.0 and drone_pitch < 0.0 and drone_pitch > -90.0:
        motor_2 += (drone_pitch/2)
        motor_3 += (drone_pitch/2)

    if roll == 0.0 and drone_roll > 0.0 and drone_roll < 90.0:
        motor_1 += (drone_roll/2)
        motor_2 += (drone_roll/2)
    elif roll == 0.0 and drone_roll < 0.0 and drone_roll > -90.0:
        motor_3 += (drone_roll/2)
        motor_4 += (drone_roll/2)

    return motor_1, motor_2, motor_3, motor_4


def cleanup(s=None):
    zero_motors()
    disconnect()
    if s:
        s.close()

# start server
try:
    s = socket(AF_INET, SOCK_STREAM)
    s.bind(("0.0.0.0", 12122))
    s.listen(1)
except:
    print("Failed to start Server...")
    cleanup(s)
    sys.exit(1)

# dps = Data per second, we need to calculate approx rate of change
#       so that a visualizer matchs real world movements
# NOTE: We do NOT actually get this exact rate, but calculate
#       close to exact in loop as dt
dps = 60
def handle_loop(conn):
    global dps

    global motor
    global telemetry
    global telemetry_connected

    # time keep
    count = 0
    at = 0
    dt = dps

    # drone settings DO NOT TAKE LIGHTLY!

    # motor_sensitivity_* is how much total 'angle' we allow the pilot
    # to have.
    motor_sensitivity_angle = 22.5
    motor_sensitivity = motor_sensitivity_angle/2

    # max throttle will be less because we can NOT spin the motors faster
    # than max speed, meaning we would loose the ability to change pitch/
    # roll/yaw...
    max_throttle = (180 - motor_sensitivity)

    # drone information to help with calculations (not used yet!)
    motor_max_power_output = 2 # lbs per motor
    total_motors = 4
    drone_total_weight = 2 # lbs
    power_to_weight_ratio = \
        ((total_motors * motor_max_power_output) / drone_total_weight)
    throttle_to_hover_ratio = 1 / power_to_weight_ratio

    # default motor values.
    motor_1 = 0
    motor_2 = 0
    motor_3 = 0
    motor_4 = 0

    drone_rotation = ""
    drone_location = ""

    drone_pitch = 0
    drone_roll  = 0
    drone_yaw   = 0

    drone_altitude = 0

    drone_last_pitch = 0
    drone_last_roll  = 0
    drone_last_yaw   = 0

    drone_last_altitude = 0

    while conn:
        try:
            t1 = datetime.now()

            if telemetry_connected:
            # get telemetry data
                try:
                    telemetry_data = telemetry.recv(4096).decode().rstrip()

                    drone_rotation = str(telemetry_data.split(":")[0])
                    drone_location = str(telemetry_data.split(":")[1])

                    drone_roll     = float(drone_rotation.split(" ")[0])
                    drone_pitch    = float(drone_rotation.split(" ")[1])
                    drone_yaw      = float(drone_rotation.split(" ")[2])

                    drone_altitude = float(drone_location.split(" ")[2])
                except Exception as e:
                    print(str("Telemetry_data Error: "))
                    print(str(e))


            # receive data and convert
            data = conn.recv(4096).decode().rstrip()
            parse = data.split(":")[0]
            pitch       = float(parse.split(" ")[0])
            roll        = float(parse.split(" ")[1])
            yaw         = float(parse.split(" ")[2])
            throttle    = float(parse.split(" ")[3])
            camera_pan  = float(parse.split(" ")[4])
            camera_tilt = float(parse.split(" ")[5])

            #print('{0} {1} {2} {3}'.format(pitch, roll, yaw, throttle))

            # for controlling pan tilt!
            #pitch += 1
            #yaw   += 1
            #motor.servo[0].angle = 180 * (yaw/2)
            #motor.servo[1].angle = 180 * (pitch/2)
            #####################################

            # HOW MOTORS SHALL BE CONNECTED
            #
            #     FORWARD (TOP DOWN)
            #
            #     3[2]  2[1]
            #      \   /
            #       ###
            #       ###
            #      /   \
            #     4[3]  1[0]
            #
            ###############################

            # make SURE values are in range! Values should be from 0.0 to 1.0
            if throttle > 0.0 and throttle <= 1.0:
                # cut max throttle for headroom on movement
                throttle = throttle * max_throttle

            # pitch forward else backwards
            if pitch > 0.0 and pitch <= 1.0:
                # check to see if throttle is above motor_sensitivity
                # to avoid a negative angle
                motor_1 = (throttle + (motor_sensitivity * pitch))
                #motor_2 = (throttle - (motor_sensitivity * pitch))
                #motor_3 = (throttle - (motor_sensitivity * pitch))
                motor_4 = (throttle + (motor_sensitivity * pitch))
            elif pitch < 0.0 and pitch >= -1.0:
                #motor_1 = (throttle + (throttle * pitch))
                motor_2 = (throttle + abs(motor_sensitivity * pitch))
                motor_3 = (throttle + abs(motor_sensitivity * pitch))
                #motor_4 = (throttle + (throttle * pitch))

            # roll right or left
            if roll > 0.0 and roll <= 1.0:
                #motor_1 = (throttle - (motor_sensitivity * roll))
                #motor_2 = (throttle - (motor_sensitivity * roll))
                motor_3 = (throttle + (motor_sensitivity * roll))
                motor_4 = (throttle + (motor_sensitivity * roll))
            elif roll < 0.0 and roll >= -1.0:
                motor_1 = (throttle + abs(motor_sensitivity * roll))
                motor_2 = (throttle + abs(motor_sensitivity * roll))
                #motor_3 = (throttle + (throttle * roll))
                #motor_4 = (throttle + (throttle * roll))

            # yaw right or left
            if yaw > 0.0 and yaw <= 1.0:
                #motor_1 = (throttle - (motor_sensitivity * yaw))
                motor_2 = (throttle + (motor_sensitivity * yaw))
                #motor_3 = (throttle - (motor_sensitivity * yaw))
                motor_4 = (throttle + (motor_sensitivity * yaw))
            elif yaw < 0.0 and yaw >= -1.0:
                motor_1 = (throttle + abs(motor_sensitivity * yaw))
                #motor_2 = (throttle + (throttle * yaw))
                motor_3 = (throttle + abs(motor_sensitivity * yaw))
                #motor_4 = (throttle + (throttle * yaw))

            if pitch == 0.0 and roll == 0.0 and yaw == 0.0:
                motor_1 = throttle
                motor_2 = throttle
                motor_3 = throttle
                motor_4 = throttle

            # set values to motors
            try:
                # if we can stabilize, we will. stabilize adds minor changes
                # to the motor values to try and make sure that the drone
                # stays up
                if telemetry_connected:
                    motor_1, motor_2, motor_3, motor_4 = \
                    stabilize_motors(\
                            [motor_1, motor_2, motor_3, motor_4], \
                            throttle, \
                            roll, pitch, yaw, \
                            drone_roll, drone_pitch, drone_yaw)

                motor.servo[0].angle = motor_1
                motor.servo[1].angle = motor_2
                motor.servo[2].angle = motor_3
                motor.servo[3].angle = motor_4

                #camera servo's
                #motor.servo[4].angle = camera_pan
                #motor.servo[5].angle = camera_tilt

                print("motor 1: " + str(motor_1))
                print("motor 2: " + str(motor_2))
                print("motor 3: " + str(motor_3))
                print("motor 4: " + str(motor_4))
            except:
                pass

            # save values as last values
            if telemetry_connected:

                drone_last_roll  = drone_roll
                drone_last_pitch = drone_pitch
                drone_last_yaw   = drone_yaw

                drone_last_altitude = drone_altitude

        except Exception as e:
            print(e)
            conn.close()
            print(str(addr) + " disconected!")
            break

        # we are at the mercy of pilot controls for loop update!
        #time.sleep(0.001)
        t2 = datetime.now()
        count += 1
        t = t2-t1
        at += (t.microseconds/1000000)
        if count == 20:
            dt = at/count
            count = 0
            at = 0

# main loop
while True:
    zero_motors()
    telemetry_connected = connect_to_telemetry()
    if telemetry_connected:
        print("Telemetry connected!")
    else:
        print("Warning! NO telemetry!")
    print("Ready!")
    try:
        conn, addr = s.accept()
        print(str(addr) + " connected!")
        handle_loop(conn)
    except KeyboardInterrupt as e:
        print("Interrupt caught: Cleaning up and exiting...")
        cleanup(s)
        exit(0)
    except Exception as e:
        print("Failed to accept connection! : " + str(e))
