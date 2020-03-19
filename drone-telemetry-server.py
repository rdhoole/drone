print("Starting...")

from board import SCL, SDA
from busio import I2C
from adafruit_lsm9ds1 import LSM9DS1_I2C, \
                             GYROSCALE_2000DPS, \
                             ACCELRANGE_2G

from adafruit_mpl3115a2 import MPL3115A2
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from threading import Thread
from socket import socket, AF_INET, SOCK_STREAM
import time
import math
import sys
from datetime import datetime

running = True
samples = 1000

def cleanup(s=None):
    if s:
        s.close()

try:
    i2c = I2C(SCL, SDA)

    sensor  = LSM9DS1_I2C(i2c)
    sensor1 = MPL3115A2(i2c)
    ads     = ADS.ADS1115(i2c)
    battery = AnalogIn(ads, ADS.P0)

    sensor.gyro_scale = GYROSCALE_2000DPS
    sensor.accel_range = ACCELRANGE_2G

    # this is here to 'zero' out the altitude
    sensor1.sealevel_pressure = int(sensor1.pressure)
    #sensor1.sealevel_pressure = 101325 # average

except:
    print("Failed to setup Sensor(s)...")
    cleanup()
    sys.exit(1)

try:
    s = socket(AF_INET, SOCK_STREAM)
    s.bind(('0.0.0.0', 12121))
    s.listen(3)
except:
    print("Failed to start Server...")
    cleanup(s)
    sys.exit(2)

def normalize_gyro():
    global samples
    a_x = a_y = a_z = 0
    count = 0
    for i in range(samples):
        x, y, z = sensor.gyro
        if i > samples/2:
            a_x += x
            a_y += y
            a_z += z
            count += 1
    return (a_x/count), (a_y/count), (a_z/count)

def normalize_accel():
    global samples
    a_x = a_y = a_z = a_g = 0
    count = 0
    for i in range(samples):
        x, y, z = sensor.acceleration
        if i > samples/2:
            a_x += x
            a_y += y
            a_z += z
            a_g += (math.sqrt(x**2 + y**2 + z**2))
            count += 1
    return (a_x/count), (a_y/count), (a_z/count), (a_g/count)

def normalize_mag():
    global samples
    a_x = a_y = a_z = 0
    count = 0
    for i in range(samples):
        x, y, z = sensor.magnetic
        if i > samples/2:
            a_x += x
            a_y += y
            a_z += z
            count += 1
    return (a_x/count), (a_y/count), (a_z/count)

try:
    offset_gx, offset_gy, offset_gz = normalize_gyro()
except:
    print("Failed to get Gyroscope offset data...")
    cleanup()
    sys.exit(3)

try:
    offset_ax, offset_ay, offset_az, offset_ag = normalize_accel()
except:
    print("Failed to get Accelerometer offset data...")
    cleanup(s)
    sys.exit(3)

try:
    offset_mx, offset_my, offset_mz = normalize_mag()
except:
    print("Failed to get Magnetometer offset data...")
    cleanup(s)
    sys.exit(3)

# update altitude
altitude = 0
altitude_update_counter = 0
def update_altitude():
    global sensor1
    global altitude
    global altitude_update_counter
    average_alt = 0
    average_amount = 2
    # try to read sensor
    try:
        # get an average
        for i in range(average_amount):
            average_alt += sensor1.altitude
        altitude = (average_alt / average_amount)
    except KeyboardInterrupt:
        print("Altitude update thread closing...")
        sys.exit(0)
    except:
        print("Failed to read Altitude...")
    finally:
        altitude_update_counter -= 1
        #print(altitude)

# update gyroscope
gx = gy = gz = 0
gyroscope_update_counter = 0
def update_gyroscope():
    global sensor
    global gx, gy, gz
    global gyroscope_update_counter

    try:
        gx, gy, gz = sensor.gyro
    except KeyboardInterrupt:
        print("Gyroscope update thread closing...")
        sys.exit(0)
    except:
        print("Failed to read Gyroscope...")
        gx = gy = gz = 0
    finally:
        gyroscope_update_counter -= 1

# update accelerometer
ax = ay = az = 0
vx = vy = vz = 0
last_vx = last_vy = last_vz = 0
accelerometer_update_counter = 0
def update_accelerometer():
    global sensor
    global ax, ay, az
    global accelerometer_update_counter

    try:
        ax, ay, az = sensor.acceleration
    except KeyboardInterrupt:
        print("Accelerometer update thread closing...")
        sys.exit(0)
    except:
        print("Failed to read Accelerometer...")
        ax = ay = az = 0
    finally:
        accelerometer_update_counter -= 1

# update magnetometer
mx = my = mz = 0
magnetometer_update_counter = 0
def update_magnetometer():
    global sensor
    global mx, my, mz
    global magnetometer_update_counter

    try:
        mx, my, mz = sensor.magnetic
    except KeyboardInterrupt:
        print("Magnetometer update thread closing...")
        sys.exit(0)
    except:
        print("Failed to read Magnetometer...")
    finally:
        magnetometer_update_counter -= 1

heading = 0
h_x = h_y = h_z = []
heading_update_counter = 0
def update_heading():
    global mx, my, mz
    global h_x, h_y, h_z
    global heading_update_counter
    global heading
    heading_update_counter += 1

    h_x.append(mx)
    h_y.append(my)
    h_z.append(mz)

    if heading_update_counter > 10:
        # apply hard iron distortion
        offset_x = (max(h_x) + min(h_x)) / 2
        offset_y = (max(h_y) + min(h_y)) / 2
        offset_z = (max(h_z) + min(h_z)) / 2

        corrected_x = mx - offset_x
        corrected_y = mx - offset_y
        corrected_z = mx - offset_z

        heading = math.atan2(corrected_y,corrected_x)*(180/math.pi)
        h_x = h_y = h_z = []
        heading_update_counter = 0

battery_voltage = 0.0
battery_average_voltage = 0
battery_percent = 0
battery_max_voltage = 1.60 # ~ 16.8v with 12v zener and 3v zener
battery_min_voltage = 0    # ~ 14.0v with ^
battery_update_counter = 0
battery_counter = 0
def update_battery():
    global battery
    global battery_percent
    global battery_voltage
    global battery_max_voltage
    global battery_min_voltage
    global battery_average_voltage
    global battery_counter
    global battery_update_counter
    try:
        #battery_average_voltage += battery.voltage
        battery_voltage = battery.voltage
    except:
        #battery_average_voltage += 0.0
        battery_voltage = battery.voltage

    #if battery_counter >= 5:
    #    battery_counter = 0
    #    battery_voltage = battery_average_voltage/5
    #    battery_average_voltage = 0

    battery_percent = \
        ((battery_voltage - battery_min_voltage) * 100) / \
        (battery_max_voltage - battery_min_voltage)

    time.sleep(.5)
    #battery_counter += 1
    battery_update_counter -= 1

print("Ready for connections.")

# dps = Data per second, we need to calculate approx rate of change
#       so that a visualizer matchs real world movements
# NOTE: We do NOT actually get this exact rate, but calculate
#       close to exact in loop as dt
dps = 60
data = ''

roll = pitch = yaw = 0
loc_x = loc_y = loc_z = 0
last_loc_x = last_loc_y = last_loc_z = 0

force_magnitude_approx = 0

# loop
def telemetry_loop():
    global data

    global battery_voltage
    global battery_percent

    global roll
    global pitch
    global yaw

    global ax, vx, last_vx
    global ay, vy, last_vy
    global az, vz, last_vz

    global mx
    global my
    global mz

    global loc_x, last_loc_x
    global loc_y, last_loc_y
    global loc_z, last_loc_z

    global altitude_update_counter
    global gyroscope_update_counter
    global accelerometer_update_counter
    global magnetometer_update_counter
    global battery_update_counter

    count = 0
    at = 0
    dt = dps

    while running:
        t1 = datetime.now()
        # normalized data from gyroscope
        roll  += (gx+(offset_gx*-1))*dt
        pitch += -(gy+(offset_gy*-1))*dt
        yaw   += (gz+(offset_gz*-1))*dt

        # normalized data from accelerometer
        ax += -(ax+(offset_ax*-1))*dt
        ay += (ay+(offset_ay*-1))*dt
        az += -(az+(offset_az*-1))*dt

        # normalized data from magnetometer
        #mx += (mx+(offset_mx*-1))*dt
        #my += (my+(offset_my*-1))*dt
        #mz += (mz+(offset_mz*-1))*dt
        mx += mx*dt
        my += my*dt
        mz += mz*dt

        # Heading is still not properly calculated
        #print(heading)

        # Complementary Filter - only apply with-in -8.0 - 8.0 g's of force
        #force_magnitude_with_gravity = math.sqrt(ax**2 + ay**2 + az**2)
        force_magnitude_with_gravity = math.sqrt(ax**2 + ay**2 + az**2)
        force_magnitude_without_gravity = force_magnitude_with_gravity + (offset_ag*-1)
        if (force_magnitude_without_gravity > -8.0 and force_magnitude_without_gravity < 8.0):
            # the a and b must equal 1, but ratio can be
            # adjusted as needed.
            a = 0.98
            b = 0.02
            # data from accelerometer
            # y to x
            rollaccl = math.atan2(ay, math.sqrt(ax**2 + az**2))*180/math.pi
            # combine with gyroscope
            roll = roll * a + rollaccl * b

            # data from accelerometer
            # x to y
            pitchaccl = math.atan2(ax, math.sqrt(ay**2 + az**2))*180/math.pi
            # combine with gyroscope
            pitch = pitch * a + pitchaccl * b

            # data from magnetometer
            #
            #yawaccl = math.atan2(-mx, my)*180/math.pi
            #yawaccl = math.atan2(az, math.sqrt(ax*ax + ay*ay))*180/math.pi
            # combine with gyroscope
            #yaw = yaw * a + yawaccl * b

            # get ax, ay, az with gravity removed
            ax = (ax/force_magnitude_with_gravity)*force_magnitude_without_gravity
            ay = (ay/force_magnitude_with_gravity)*force_magnitude_without_gravity
            az = (az/force_magnitude_with_gravity)*force_magnitude_without_gravity

            # get velocity
            vx += ax
            vy += ay
            vz += az

            # VERY close to getting the velocity right
            # but accelerometer drifts to much AND
            # has inaccurate reading with roll/pitch

            # low pass filter
            #a = 0.5
            #vz = (a * vz) + (1-a) * (last_vz)

            last_vx = vx
            last_vy = vy
            last_vz = vz

            #print(vz)

            # attempt at updating location from sensors
            #loc_x = (last_loc_x + vx)
            #loc_y = (last_loc_y + vy)
            #loc_z = vz

            # use filter to smooth altitude with last position
            loc_z = ((last_loc_z * 0.95) + (altitude * 0.05))

            # update last location...
            last_loc_x = loc_x
            last_loc_y = loc_y
            last_loc_z = loc_z


        data = '{0:0.3f} {1:0.3f} {2:0.3f}:'.format(-pitch, roll, yaw)
        data += '{0:0.3f} {1:0.3f} {2:0.3f}:'.format(loc_x, loc_y, loc_z)
        data += '{0:0.2f} {1:0.2f} \n'.format(battery_voltage, battery_percent)
        #print(data)

        # UPDATE at end of loop to give threads a chance to get
        # data

        # NOTE: performance is actually better having gyroscope
        #       and accelerometer not threaded, and have the
        #       altitude start in a thread.

        # update altitude
        if (altitude_update_counter < 1):
            altitude_update_counter += 1
            Thread(target=update_altitude).start()
            #update_altitude()

        # update gyroscope
        if (gyroscope_update_counter < 1):
            gyroscope_update_counter += 1
            #threading.Thread(target=update_gyroscope).start()
            update_gyroscope()

        # update accelerometer
        if (accelerometer_update_counter < 1):
            accelerometer_update_counter += 1
            #threading.Thread(target=update_accelerometer).start()
            update_accelerometer()

        # update magnetometer
        if (magnetometer_update_counter < 1):
            magnetometer_update_counter += 1
            update_magnetometer()

        # update battery info
        if (battery_update_counter < 1):
            battery_update_counter += 1
            Thread(target=update_battery).start()

        # update heading
        update_heading()

        time.sleep(1/dps)
        # we get the average of the REAL amount of time it goes through
        # the loop to get more accurate reading from sensors
        t2 = datetime.now()
        count += 1
        t = t2-t1
        at += (t.microseconds/1000000)
        if count == 20:
            dt = at/count
            count = 0
            at = 0

def client_handler(conn, addr):
    global dps
    global data
    while conn:
        try:
            conn.send(data.encode())
            time.sleep(1/dps)
        except:
            conn.close()
            print(str(addr) + " disconnected!")
            break

# start telemetry loop
Thread(target=telemetry_loop).start()
# main loop
while True:
    try:
        conn, addr = s.accept()
        print(str(addr) + " connected!")
        Thread(target=client_handler, args=[conn, addr]).start()
        #print(str(addr) + "disconnected!")
    except KeyboardInterrupt as e:
        print("Interrupt caught: Cleaning up and exiting...")
        running = False
        cleanup(s)
        exit(0)
    except:
        print("Failed to accept connection!")
