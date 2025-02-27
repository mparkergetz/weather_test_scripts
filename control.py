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
import queue


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
print('Logging')
logging.info("Begin logging data")

# Sync threads
stop_event = threading.Event()
csv_queue = queue.Queue()

def sensor_data():
    while not stop_event.is_set():
        time_current = datetime.now()
        sensors.add_data(time_current)
        
        next_run = time.monotonic() + 2  
        while time.monotonic() < next_run:
            time.sleep(0.1)

def csv_writer():
    while not stop_event.is_set() or not csv_queue.empty():
        try:
            print(' getting from queue')
            data = csv_queue.get(timeout=1)  # get data from queue (wait max 1 sec)
            if data:
                print('data present, appending')
                sensors.append_to_csv(data)
            csv_queue.task_done()
            print('csv_queue task done')
        except queue.Empty:
            print('csv queue empty')
            pass 


sensor_thread = threading.Thread(target = sensor_data)
sensor_thread.start()

csv_thread = threading.Thread(target=csv_writer, daemon=True)
csv_thread.start()

try:
    curr_time = time.monotonic()
    next_display_time = time.monotonic() + 1

    while True:
        readings = sensors.latest_readings
       # GOOD

        if None not in readings.values():
            if time.monotonic() >= next_display_time:
                disp.display_sensor_data(
                    readings["temperature"],
                    readings["relative_humidity"],
                    readings["pressure"],
                    readings["wind_speed"]
                )
                next_display_time += 1

        if time.monotonic() - curr_time >= 10:
            print(psutil.cpu_percent(interval=None), "% CPU Usage") 
            csv_queue.put(readings)
            print('added to queue:', readings)
            curr_time = time.monotonic()

        time.sleep(0.1) 

except KeyboardInterrupt:
    stop_event.set()
    sensor_thread.join()
    
    while not csv_queue.empty():
        data = csv_queue.get()
        sensors.append_to_csv(data)
        csv_queue.task_done()
    
    csv_thread.join()

    disp.display_msg('Interrupted')
    logging.info("KeyboardInterrupt")
    sys.exit()

except:
    disp.display_msg('Error')
    logging.exception("Error recording sensor data")
    sys.exit()