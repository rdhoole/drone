# Drone
Design of the drone currently is **too** bulky, and should be redesigned using 2x[Adafruit Feather M0 with RFM95 LoRa Radio - 900MHz - RadioFruit](https://www.adafruit.com/product/3178) (as command and control)
</br>
___
This is a project to create a drone pretty much from scratch with a Jetson Nano as the computer reading and controlling the devices needed. </br>
It uses:
- [Adafruit LSM9DS1 Accelerometer + Gyro + Magnetometer 9-DOF Breakout](https://learn.adafruit.com/adafruit-lsm9ds1-accelerometer-plus-gyro-plus-magnetometer-9-dof-breakout/overview)
- [Adafruit 8-Channel PWM or Servo FeatherWing](https://learn.adafruit.com/adafruit-8-channel-pwm-or-servo-featherwing/downloads)
- [Adafruit Mini GPS PA1010D Module](https://learn.adafruit.com/adafruit-mini-gps-pa1010d-module)
- [MPL3115A2 - I2C Barometric Pressure/Altitude/Temperature Sensor](https://www.adafruit.com/product/1893)

Example of progress:
 1. [Telemetry](https://www.youtube.com/watch?v=Ij3bfACrW_U) -
This is actually the flight controller that is ran on the laptop and allows for an after market Xbox controller to operated the drone, but demonstrates that the telemetry server is working.
 2. [Controls working together](https://www.youtube.com/watch?v=-wORpTOL3Kg) - This is being controlled from a Xbox controller programed to control the drone through an user interface shown in the first video.
