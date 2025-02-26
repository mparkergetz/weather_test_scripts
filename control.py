#!/usr/bin/env python3
import os
import sys
import logging
from .config import Config
from .display import Display
from .sensors import MultiSensor
from time import sleep
from datetime import datetime
import threading
import time
import psutil
"""
Image2 is the current version of the imaging script for writing the sensor data to csv


Functionality:
- Saves Sensor data to dictionary and after [30 seconds] appends to csv. 
It is important to note that if you kill the script that any data that has been saved 
into this dictionary will immediately be appended to the csv file and the last recorded images will also be written.
- The sensor and imaging timestamps are in sync and this can be validated from the log file.

TO DO:
- Finalize Solar Testing and Verify with the voltage difference thing to make sure that our readings are good for the single cell
- Then attempt to test with the multi cell 10050mah module...
- Provide error handling for solar and voltage/power of pi...
    -  Purchase a device that will do this...

- Need to implement the night time imaging threshold based on the light sensor
- Battery data need to log this data and write...
- Keep pi and witty pi on for long duration...
- Determine RTC alternative...
- add in the GPS Sensor Functionality





"""


config = Config()

name = config['general']['name']    
# size = (config['imaging'].getint('w'), config['imaging'].getint('h'))
# lens_position = config['imaging'].getfloat('lens_position')
# img_count = 0


# set main and sub output dirs
main_dir = "/home/pi/data/"
date_folder = str(datetime.now().strftime("%Y-%m-%d"))
curr_date = os.path.join(main_dir, date_folder)
os.makedirs(curr_date , exist_ok=True)
## image data will save to a sub directory 'images'
path_image_dat = os.path.join(curr_date,'images')

os.makedirs(path_image_dat, exist_ok=True)
## sensor data will save to current data directory
path_sensor_dat = curr_date 


# Initialize the sensors...
## also initializes the csv file name timestamp
sensors = MultiSensor(path_sensor_dat)

# Initialize the display
disp = Display()
disp.display_msg('Initializing')

# Configure logging
log_file = "/home/pi/weather.log"
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("###################### NEW RUN ##################################")

# try:
#     camera = Picamera2()
#     cam_config = camera.create_still_configuration({'size': size})
#     camera.configure(cam_config)
#     camera.exposure_mode = 'sports'
#     camera.set_controls({"LensPosition": lens_position})
#     camera.start()
#     sleep(5)
# except:
#     disp.display_msg('Cam not connected', img_count)
#     logging.error("Camera init failed")
#     sys.exit()



# go to working dir
os.chdir(curr_date)
print('Logging')
logging.info("Begin logging data")

time_current = datetime.now()
def sensor_data():
    # wait for event to be set
    event.wait()
    time_current_split = str(time_current.strftime("%Y%m%d_%H%M%S"))
    ## add data to sensor dictionary
    sensors.add_data(name,time_current_split )
    # print(f"Sensor Data Acquired: {time_current_split}")
    #print("Image acquired: ", time_current_split)

    # # Save sensor data to csv immediately:
    # sensors.append_to_csv()
# def capture_image():
#     # wait for the event to be set...
#     event.wait()
#     time_current_split = str(time_current.strftime("%Y%m%d_%H%M%S"))
#     camera.capture_file('images/'+name + '_' + time_current_split + '.jpg')
#     # print(("Image acquired: %s", time_current_split))
#     logging.info("Image acquired: %s", time_current_split)
#     #print("Image acquired: ", time_current_split)

# MAX_RETRIES = 3
# retry_count = 0

# Start timer for the sensors
curr_time = time.time()
while True:

    try:
        # disp.display_msg('Imaging!', img_count)

        # Create the Event
        event =  threading.Event()
        # set the event
        event.set()
        # develop two threads, one for sensors and one for images
        sensor_thread = threading.Thread(target = sensor_data)
        capture_thread = threading.Thread(target=capture_image)
        ## get the current time
        time_current = datetime.now()
        time_current_split = str(time_current.strftime("%Y%m%d_%H%M%S"))
        # print(time_current_split)
        # start the sensor thread and capture thread:
        sensor_thread.start()
        capture_thread.start()

        # Main thread waits for the threads to finish
        ## first waits for this longer thread to complete first (3 seconds)
        capture_thread.join(timeout=3) 
        ## then will check if the sensor_thread is still alive and wait if needed 
        sensor_thread.join() 

        # If thread is still alive after 3 seconds, it's probably hung
        if capture_thread.is_alive():
            raise TimeoutError("Camera operation took too long!")
        
        img_count += 1
        retry_count = 0
       
        # if wanting a delay in saving sensor data:
        if (time.time()-curr_time) >= 60:
            print(psutil.cpu_percent(interval=1),"%")
            sensors.append_to_csv()
            curr_time = time.time()
        sleep(.7)
    except KeyboardInterrupt:
        if len(list(sensors.data_dict.values())[0]) != 0: 
            # if list is not empty then add data...
            sensors.append_to_csv()
        
        disp.display_msg('Interrupted', img_count)
        sensors.sensors_deint()
        logging.info("KeyboardInterrupt")
        sys.exit()
    except TimeoutError:
        retry_count += 1
        disp.display_msg('Cam Timeout!', img_count)
        logging.error("Camera operation timeout!")
        if retry_count >= MAX_RETRIES:
            disp.display_msg('Max retries reached!', img_count)
            logging.error("Max retries reached. Exiting...")
            sys.exit()
        else:
            # Wait for a bit before attempting a retry
            sleep(2)
            continue
    except:
        disp.display_msg('Error', img_count)
        logging.exception("Error capturing image")
        sys.exit()

