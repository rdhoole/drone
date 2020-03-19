# Drone
**Progress has paused :(** </br></br>
I have decided to put this up in case someone may need help getting started. However, my design of the drone currently is **too** bulky, and I will be redesigning it using 2x[Adafruit Feather M0 with RFM95 LoRa Radio - 900MHz - RadioFruit](https://www.adafruit.com/product/3178) (one that drives the drone and the other that send commands and receives updates from the drone)
</br></br>
This is a project to create a drone pretty much from scratch with a Jetson Nano as the computer reading and controlling the devices needed. </br>
It uses:
- [Adafruit LSM9DS1 Accelerometer + Gyro + Magnetometer 9-DOF Breakout](https://learn.adafruit.com/adafruit-lsm9ds1-accelerometer-plus-gyro-plus-magnetometer-9-dof-breakout/overview)
- [Adafruit 8-Channel PWM or Servo FeatherWing](https://learn.adafruit.com/adafruit-8-channel-pwm-or-servo-featherwing/downloads)
- [Adafruit Mini GPS PA1010D Module](https://learn.adafruit.com/adafruit-mini-gps-pa1010d-module)
- [MPL3115A2 - I2C Barometric Pressure/Altitude/Temperature Sensor](https://www.adafruit.com/product/1893)

Example of progress, https://www.youtube.com/watch?v=Ij3bfACrW_U </br>
This is actually the flight controller that is ran on the laptop and allows for an after market Xbox controller to operated the drone, but demonstrates that the telemetry server is working.
