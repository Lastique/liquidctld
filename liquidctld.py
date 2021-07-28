#!/usr/bin/python3

import os
import time
# https://github.com/liquidctl/liquidctl
from liquidctl import find_liquidctl_devices

device_name = 'H115i'

temp_down = 55
temp_up = 70
pump_mode_down = 'quiet'
pump_mode_up = 'balanced'
led_color = [0, 0, 0]

monitoring_interval = 5


def find_liquidctl_device(device_name):
    devices = find_liquidctl_devices()

    for dev in devices:
        if device_name in dev.description:
            return dev

    return None


def find_temp_input_filename():
    for hwmon in os.listdir('/sys/class/hwmon'):
        try:
            with open('/sys/class/hwmon/' + hwmon + '/name') as name_file:
                line = name_file.readline()
                if line.strip() == 'coretemp' and os.path.isfile('/sys/class/hwmon/' + hwmon + '/temp1_input'):
                    return '/sys/class/hwmon/' + hwmon + '/temp1_input'

        except IOError:
            continue

    return None

def read_temp(temp_filename):
    try:
        with open(temp_filename) as temp_file:
            return int(temp_file.readline().strip()) / 1000

    except IOError as e:
        print(f'Failed to read CPU temp: {e}')

    except ValueError as e:
        print(f'Failed to parse CPU temp: {e}')

    return -1

def set_led_colors(device, mode, colors):
    with device.connect():
        device.set_color(channel = 'pump', mode = mode, colors = colors)

def set_pump_mode(device, mode):
    with device.connect():
        device.initialize(pump_mode = mode)

device = find_liquidctl_device(device_name)
if device is None:
    print(f'Device {device_name} not found')
    exit(-1)

temp_filename = find_temp_input_filename()
if temp_filename is None:
    print('CPU temperature sensor file not found')
    exit(-1)

# Set LED colors
set_led_colors(device, 'fixed', [led_color])

# Start temp monitoring loop
last_temp = 0

while True:
    temp = read_temp(temp_filename)
    #print(f'CPU temperature: {temp}')
    if temp > 0:
        if temp > last_temp:
            if last_temp == 0:
                if temp >= temp_up:
                    set_pump_mode(device, pump_mode_up)
                else:
                    set_pump_mode(device, pump_mode_down)
            elif last_temp < temp_up and temp >= temp_up:
                #print(f'CPU temperature went from {last_temp} to {temp}')
                set_pump_mode(device, pump_mode_up)
        elif temp < last_temp:
            if last_temp > temp_down and temp <= temp_down:
                #print(f'CPU temperature went from {last_temp} to {temp}')
                set_pump_mode(device, pump_mode_down)

        last_temp = temp

    time.sleep(monitoring_interval)
