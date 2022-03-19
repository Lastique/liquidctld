#!/usr/bin/python3

import os
import time
# https://github.com/liquidctl/liquidctl
from liquidctl import find_liquidctl_devices

device_name = 'H115i'

# LED color to set on startup
led_color = [0, 0, 0]

# CPU temperature to reduce pump speed
temp_down = 55
# CPU temperature to increase pump speed
temp_up = 70
# Low and high pump speeds
pump_modes = ['quiet', 'balanced']

# The number of check intervals CPU temp has to remain no higher than the low theshold to reduce the pump speed
down_intervals = 7
# The number of check intervals CPU temp has to remain no lower than the high theshold to increase the pump speed
up_intervals = 3

# Temperature checking interval while we're not in transition between pump speeds
stable_checking_interval = 2
# Temperature checking interval while we're in transition between pump speeds
transient_checking_interval = 1


current_pump_mode = None

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
        device.set_color(channel = 'led', mode = mode, colors = colors)

def set_pump_mode(device, mode):
    global current_pump_mode
    with device.connect():
        device.initialize(pump_mode = pump_modes[mode])
    current_pump_mode = mode

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
transitioning = 0
transition_intervals = 0

while True:
    temp = read_temp(temp_filename)
    if temp > 0:
        if current_pump_mode is None:
            set_pump_mode(device, 1 if temp >= temp_up else 0)
        else:
            if current_pump_mode != 1 and temp >= temp_up:
                if transitioning < 1:
                    transitioning = 1
                    transition_intervals = 0
                if transition_intervals < up_intervals:
                    transition_intervals += 1
                else:
                    set_pump_mode(device, 1)
                    transitioning = 0
                    transition_intervals = 0
            elif current_pump_mode != 0 and temp <= temp_down:
                if transitioning > -1:
                    transitioning = -1
                    transition_intervals = 0
                if transition_intervals < down_intervals:
                    transition_intervals += 1
                else:
                    set_pump_mode(device, 0)
                    transitioning = 0
                    transition_intervals = 0
            elif transitioning != 0:
                transitioning = 0
                transition_intervals = 0

    #print(f'CPU temperature: {temp}, pump mode: {current_pump_mode}, transitioning: {transitioning}, transition intervals: {transition_intervals}')
    time.sleep(stable_checking_interval if transitioning == 0 else transient_checking_interval)
