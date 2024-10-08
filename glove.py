import adafruit_rfm9x
import busio
import board
import time
import digitalio
from adafruit_lsm6ds.lsm6dsox import LSM6DSOX as LSM6DS
from busio import I2C
from adafruit_lis3mdl import LIS3MDL
from adafruit_debouncer import Debouncer

# BOARD
i2c = I2C(board.SCL, board.SDA)  # Create library object using our Bus I2C port
accel_gyro = LSM6DS(i2c)
mag = LIS3MDL(i2c)

# LORA
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = digitalio.DigitalInOut(board.D9)
reset = digitalio.DigitalInOut(board.D10)
rfm9x = adafruit_rfm9x.RFM9x(spi, cs, reset, 915.0, baudrate=1000000)

# Var Inits
on = True
acceleration = [0, 0, 0]
ax_bias = 0
ay_bias = 0
az_bias = 0
gyro = [0, 0, 0]
gx_bias = 0
gy_bias = 0
gz_bias = 0

# Button 1
pin1 = digitalio.DigitalInOut(board.D6)
pin1.direction = digitalio.Direction.INPUT
pin1.pull = digitalio.Pull.UP
switch1 = Debouncer(pin1)

# Button 2
pin2 = digitalio.DigitalInOut(board.D5)
pin2.direction = digitalio.Direction.INPUT
pin2.pull = digitalio.Pull.UP
switch2 = Debouncer(pin2)


def button_1_short_press():
    rfm9x.send('on_off()')
    global on
    on = not on


def button_1_long_press():
    rfm9x.send('reset()')


def button_2_short_press():
    rfm9x.send('start()')


def button_2_long_press():
    global ax_bias, ay_bias, az_bias, gx_bias, gy_bias, gz_bias
    acceleration = accel_gyro.acceleration
    ax_bias = acceleration[0]
    ay_bias = acceleration[1]
    az_bias = acceleration[2]
    gyro = accel_gyro.gyro
    gx_bias = gyro[0]
    gy_bias = gyro[1]
    gz_bias = gyro[2]


# MAIN EXECUTE LOOP
dT = 0.0083  # Clock Speed: 8.3ms / 120 hz / 120 times a second
cooldown = 0
position = 7
tilt_cooldown = 0
rotation = 0
S1Timer = 0
S2Timer = 0
while True:
    switch1.update()
    S1Timer += 1
    if switch1.fell:
        S1Timer = 0
    if switch1.rose:
        if S1Timer > 90:
            button_1_long_press()
        else:
            button_1_short_press()

    if on:
        gyro = accel_gyro.gyro
        gx = gyro[0] - gx_bias
        gy = gyro[1] - gy_bias
        gz = gyro[2] - gz_bias
        acceleration = accel_gyro.acceleration
        ax = acceleration[0] - ax_bias
        ay = acceleration[1] - ay_bias
        az = acceleration[2] - az_bias

        S2Timer += 1
        switch2.update()
        if switch2.fell:
            S2Timer = 0
        if switch2.rose:
            if S2Timer > 90:
                button_2_long_press()
            else:
                button_2_short_press()

        x_tilt = (
            abs(ay) > 6.0
            or abs(az) > 6.0
            or abs(gz) > 1.5
            or abs(gy) > 1.5
            or abs(gx) > 1.5
        )
        cooldown -= 1
        tilt_cooldown -= 1

        if not x_tilt and cooldown < 0:
            if ax < -2.5:
                rfm9x.send('move_left()')
                position += 1
                if position > 15:
                    position = 15

                if ax < -4.5:
                    cooldown = 15
                else:
                    cooldown = 60

            if ax > 2.5:
                rfm9x.send('move_right()')
                position -= 1
                if position < 0:
                    position = 0
                if ax > 4.5:
                    cooldown = 15
                else:
                    cooldown = 60

        if tilt_cooldown < 0:
            if ay > 5.0:
                rfm9x.send('rotation()')
                rotation += 1
                if rotation > 3:
                    rotation = 0

                if ay > 8.0:
                    tilt_cooldown = 30
                else:
                    tilt_cooldown = 80

            if ay < -6.0:
                rfm9x.send('hard_drop()')
                tilt_cooldown = 120

            elif ay < -4.0:
                rfm9x.send('soft_drop()')
                tilt_cooldown = 10

    time.sleep(dT)
