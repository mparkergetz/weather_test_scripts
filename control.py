#!/usr/bin/env python3
import os
import sys
import logging
from config import Config
from sensors import Display
from sensors import MultiSensor
from time import sleep
from datetime import datetime
import threading
import time
import psutil
import board

"""
Functionality:
- Saves Sensor data to dictionary and after [30 seconds] appends to csv. 
- If you kill the script any data that has been saved into this dictionary will be appended to the csv file.
"""

config = Config()

name = config['general']['name']
output_dir = config['general']['output_dir']

#data_dir = os.path.join(output_dir,name)
date_folder = str(datetime.now().strftime("%Y%m%d"))
curr_date = os.path.join(output_dir, name, date_folder)
os.makedirs(os.path.join(output_dir, name), exist_ok=True)

# Initialize the sensors...
## also initializes the csv file name timestamp

shared_i2c = board.I2C()
sensors = MultiSensor(curr_date, i2c=shared_i2c)

# Initialize the display
disp = Display(i2c=shared_i2c)
disp.display_msg('Initializing')

# Configure logging
log_file = "/home/pi/weather.log"
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("###################### NEW RUN ##################################")

# go to working dir
#os.chdir(curr_date)
print('Logging')
logging.info("Begin logging data")

# Sync threads
stop_event = threading.Event()

def sensor_data():
    while not stop_event.is_set():
        time_current = datetime.now()
        sensors.add_data(time_current)
        time.sleep(2)

sensor_thread = threading.Thread(target = sensor_data)
sensor_thread.start()

try:
    curr_time = time.time()

    while True:
        readings = sensors.latest_readings 

        if None not in readings.values():
            disp.display_sensor_data(
                readings["temperature"],
                readings["relative_humidity"],
                readings["pressure"],
                readings["wind_speed"]
            )

        if (time.time() - curr_time) >= 10:
            print(psutil.cpu_percent(interval=1), "% CPU Usage")
            sensors.append_to_csv()
            curr_time = time.time()

except KeyboardInterrupt:
    stop_event.set()
    sensor_thread.join()
    if len(list(sensors.data_dict.values())[0]) != 0: 
        sensors.append_to_csv()
    
    disp.display_msg('Interrupted')
    logging.info("KeyboardInterrupt")
    sys.exit()

except:
    disp.display_msg('Error')
    logging.exception("Error recording sensor data")
    sys.exit()