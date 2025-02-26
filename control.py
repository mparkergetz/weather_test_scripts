#!/usr/bin/env python3
import os
import sys
import logging
from config import Config
from display import Display
from sensors import MultiSensor
from time import sleep
from datetime import datetime
import threading
import time
import psutil

"""
Functionality:
- Saves Sensor data to dictionary and after [30 seconds] appends to csv. 
- If you kill the script any data that has been saved into this dictionary will be appended to the csv file.
"""

config = Config()

name = config['general']['name']    
#output_dir = "/home/pi/data/"
output_dir = config['general']['output_dir']

#data_dir = os.path.join(output_dir,name)
date_folder = str(datetime.now().strftime("%Y%m%d"))
curr_date = os.path.join(output_dir, name, date_folder)
os.makedirs(os.path.join(output_dir, name), exist_ok=True)

# Initialize the sensors...
## also initializes the csv file name timestamp
sensors = MultiSensor(curr_date)

# Initialize the display
disp = Display()
disp.display_msg('Initializing')

# Configure logging
log_file = "/home/pi/weather.log"
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("###################### NEW RUN ##################################")

# go to working dir
#os.chdir(curr_date)
print('Logging')
logging.info("Begin logging data")

time_current = datetime.now()
def sensor_data():
    # wait for event to be set
    event.wait()
    time_current_split = datetime.now()
    ## add data to sensor dictionary
    sensors.add_data(time_current_split )
    # print(f"Sensor Data Acquired: {time_current_split}")
    #print("Image acquired: ", time_current_split)

    # # Save sensor data to csv immediately:
    # sensors.append_to_csv()

curr_time = time.time()
while True:

    try:
        # Create the Event
        event =  threading.Event()
        # set the event
        event.set()
 
        sensor_thread = threading.Thread(target = sensor_data)

        ## get the current time
        time_current = datetime.now()
        time_current_split = str(time_current.strftime("%Y%m%d_%H%M%S"))

        sensor_thread.start()
        sensor_thread.join() 

        retry_count = 0
       
        # if wanting a delay in saving sensor data:
        if (time.time()-curr_time) >= 10:
            print(psutil.cpu_percent(interval=1),"%")
            sensors.append_to_csv()
            curr_time = time.time()
        sleep(.7)

    except KeyboardInterrupt:
        if len(list(sensors.data_dict.values())[0]) != 0: 
            # if list is not empty then add data...
            sensors.append_to_csv()
        
        disp.display_msg('Interrupted')
        sensors.sensors_deinit()
        logging.info("KeyboardInterrupt")
        sys.exit()

    except:
        disp.display_msg('Error')
        logging.exception("Error recording sensor data")
        sys.exit()

