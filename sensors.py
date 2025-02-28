from datetime import datetime,timedelta
import os
import sys
import time

import socket
import fcntl
import struct

import board
from csv import DictWriter

from smbus2 import SMBus
import adafruit_sht31d # temp humidity
import adafruit_bmp3xx # pressure
import adafruit_mcp3421.mcp3421 as ADC # anemometer adc
from adafruit_mcp3421.analog_in import AnalogIn


from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306 # display

from config import Config
config = Config()
name = config['general']['name']  

class ShutdownTime(Exception):
    """Raised when the shutdown time is reached. This time will change on reboot"""
    pass

class WittyPi():
    """
    Sensor class specific to the UUGear WittyPi 4 Mini

    Current Issues:
        -  The current issue is that we are unable to get the correct RTC time on the pi when we want to sync
        - The solution for this is to instead utilize the GPS RTC first to write to the system time and then write the sytstem time to the WittyPi. That way we have complete accuracy...
            - we could use the other RTC but the wittypi has more robust functionality for startup and shutdown based on the datetime and ensuring the time accuracy is important
        - Do some troubleshooting in order to check the differences in the system, RTC from GPS and the wittypi RTC

    Upon initalizing this sensor when the board is booted the GPS Sensor RTC will be written to the WittyPi. This should be done by using a BashScript...
    
    Weekdays:
    Sunday = 0
    Monday =1
    Tuesday =2
    Wednesday = 3
    Thursday=4
    Friday=5
    Saturday =6



    TODO->

    First need to create an set SHUTDOWN METHOD! AND THEN WE GET THE TIME

    THEN WHEN WE OPEN THE WITTYPI again if we need a new fresh object which is likely then that means that we will need to also then 
    input that shutdown desired time... and so once that time has hit then we will add an extra 5 min to it and that is what we will send to the registers...


    """
    def __init__(self, bus_num= 1):
        self._bus_num = bus_num
        self._bus = None
        # Shutdown
        self._shutdown_datetime = ""
        self._time_to_shutdown = timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0)

        # Startup
        self._startup_datetime = ""
        self._time_to_startup = timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0)

        # # Data:
        # self.data_dict = {}
        # main_dir = "/home/pi/data/"
        # start_time= datetime.now().strftime('%Y%m%d_%H%M%S')
        # date_folder = str(datetime.now().strftime("%Y-%m-%d"))
        # path_sensors = os.path.join(main_dir, date_folder)
        # self._filename = f'{path_sensors}/temp_data_{start_time}.csv'# all data is written to this CSV...
    def __enter__(self):
        """return the SMBus object"""
        self._bus = SMBus(self._bus_num)
        return self
    def __exit__(self,exception_type, exception_value, exception_traceback):
        """close the bus"""
        self._bus.close()
    
    def int_to_bcd(self,value):
        """
        Convert an integer to its BCD representation.
        
        Args:
        - value: The integer value to convert (0-99).
        
        Returns:
        - The BCD representation as an integer.
        """
        return ((value // 10) << 4) | (value % 10)
    def bcd_to_int(self, bcd):
        """
        This method converts BCD-encoded value to an integer.
        """
        return ((bcd & 0xF0) >> 4) * 10 + (bcd & 0x0F)
    def weekday_conv(self, val):
        return (val + 1) % 7
    
    def get_current_time(self):
        """
        Get the current time on the WittyPi 4 mini
        
        datetime.now() could be used but for redundancy sake this method will be used just in case. Regardless the WittyPi should have a similar if not the same time as datetime.now()
        """
        time_list = []
        for i in range(58,65):

            time_list.append(self.bcd_to_int(self._bus.read_byte_data(8,i)))
        print(time_list)
        sec,min,hour,days,weekday,month,year= time_list
        curr_time = datetime(year = year+2000, month = month, day=days,hour = hour,minute=min,second=sec)
        return curr_time
    def get_shutdown_datetime(self, hr=20, min=0, sec=0):
        """
        hr - default hour set to 8pm
        
        min - default minutes set to 0

        sec - default seconds set to 0

        get the datetime for when shutdown will occur
        sets the shutdown to occur at 8pm (TEST CASE 9:30 pm)

        The actual shutdown executed by the shutdown script will happen at 9:35pm to give a bit more buffer
        """
        curr_time = self.get_current_time()
        # Set the shutdown time for today (will be 8pm normally but 9:30pm if testing!)
        self._shutdown_datetime= curr_time.replace(hour=hr,minute=min, second=sec)# amount of time until shutdown (at least 3 minutes)
        # self._shutdown_datetime += timedelta(minutes=2) # added 2 minutes until shutdown
        print(self._shutdown_datetime)
        print(self._shutdown_datetime >= datetime.now())
        return self._shutdown_datetime
    def get_shutdown_datetime_5min(self):
        """
        get the datetime for when shutdown will occur
        
        this is a test case that has shutdown occur in 5 minutes time
        """
        curr_time = self.get_current_time()
        self._time_to_shutdown = timedelta(minutes=5) # amount of time until shutdown (at least 3 minutes)
        self._shutdown_datetime = curr_time +self._time_to_shutdown # time that system will shutdown
        print(self._shutdown_datetime)
        print(self._shutdown_datetime >= datetime.now())
        return self._shutdown_datetime

    def shutdown(self):
        """
        Shutdown method for communicating to the WittyPin 4 mini
        to shutdown at 7pm...
        
        Uses registers 32-36
        
        shutdown is triggered when greater or equal to shutdown time... so when reaching shutdown... then add 5min to current time
        and signal the shutdown
        
        shutdown at 7:05pm or 9:35pm
        """
        # with SMBus(1) as bus:
        # Read RTC time from the WittyPi [IT IS ALREADY IN INT VALUES]st
        shutdown_datetime = self.get_current_time()
        # Add a 5 minute buffer to the shutdown time of 7pm or (9:30pm if TEST)
        shutdown_datetime += timedelta(minutes=5)
        print("shutdown time:",shutdown_datetime)
        # Add five minutes to the shutdown time just in case...
        shutdown_time_list = [shutdown_datetime.second,shutdown_datetime.minute ,shutdown_datetime.hour,shutdown_datetime.day,self.weekday_conv(datetime.weekday(shutdown_datetime))]
        shutdown_year = shutdown_datetime.year
        shutdown_month = shutdown_datetime.month
        for count, val in enumerate(range(32,37)):
        # print(val, shutdown_time_list[count],BCDConversion(shutdown_time_list[count]))
            self._bus.write_byte_data(8,val,self.int_to_bcd(shutdown_time_list[count]))
            time.sleep(5)
        if self.bcd_to_int(self._bus.read_byte_data(8,40)) == 0:
            print("ALARM2 AKA SHUTDOWN: NOT TRIGGERED")
            shut_list = []
            for i in range(32,37):
                shut_list.append(self.bcd_to_int(self._bus.read_byte_data(8,i)))
            sec,min,hour,days,weekday =  shut_list
            print(datetime(year = shutdown_year, month = shutdown_month, day=days,hour = hour,minute=min,second=sec))

        elif self.bcd_to_int(self._bus.read_byte_data(8,40)) == 1:
            print("ALARM2 AKA SHUTDOWN: TRIGGERED")
            print("Shutdown Time:\n")
            shut_list = []
            for i in range(32,37):
                shut_list.append(self.bcd_to_int(self._bus.read_byte_data(8,i)))
            sec,min,hour,days,weekday= shut_list
            # Python3 program for the above approach 
            print(datetime(year = shutdown_year, month = shutdown_month, day=days,hour = hour,minute=min,second=sec))
        
    def shutdown_5min(self):
        """
        Shutdown method for communicating to the WittyPin 4 mini
        to shutdown in 5 minutes time from the current time
        
        Uses registers 32-36
        
        shutdown is triggered when greater or equal to shutdown time... so when reaching shutdown... then add 5min to current time
        and signal the shutdown
        
        """
        # with SMBus(1) as bus:
        # Read RTC time from the WittyPi [IT IS ALREADY IN INT VALUES]st
        shutdown_datetime = self.get_current_time() # 
        shutdown_datetime += timedelta(minutes=5)
        # Add five minutes to the shutdown time just in case...
        shutdown_time_list = [shutdown_datetime.second,shutdown_datetime.minute ,shutdown_datetime.hour,shutdown_datetime.day,self.weekday_conv(datetime.weekday(shutdown_datetime))]
        shutdown_year = shutdown_datetime.year
        shutdown_month = shutdown_datetime.month
        for count, val in enumerate(range(32,37)):
        # print(val, shutdown_time_list[count],BCDConversion(shutdown_time_list[count]))
            self._bus.write_byte_data(8,val,self.int_to_bcd(shutdown_time_list[count]))
            time.sleep(5)
        if self.bcd_to_int(self._bus.read_byte_data(8,40)) == 0:
            print("ALARM2 AKA SHUTDOWN: NOT TRIGGERED")
            shut_list = []
            for i in range(32,37):
                shut_list.append(self.bcd_to_int(self._bus.read_byte_data(8,i)))
            sec,min,hour,days,weekday =  shut_list
            print(datetime(year = shutdown_year, month = shutdown_month, day=days,hour = hour,minute=min,second=sec))

        elif self.bcd_to_int(self._bus.read_byte_data(8,40)) == 1:
            print("ALARM2 AKA SHUTDOWN: TRIGGERED")
            print("Shutdown Time:\n")
            shut_list = []
            for i in range(32,37):
                shut_list.append(self.bcd_to_int(self._bus.read_byte_data(8,i)))
            sec,min,hour,days,weekday= shut_list
            # Python3 program for the above approach 
            print(datetime(year = shutdown_year, month = shutdown_month, day=days,hour = hour,minute=min,second=sec))
    def startup(self,hr=5,min=0,sec=0):
        """

        hr -> default 5 (5am)

        min -> default 0

        sec -> default 0

        This method sets the startup time registers on the WittyPi 4 mini 
        
        In this case it sets the start up time to be 7am or 9:45pm 
        """
        # SET STARTUP!
        ## get the current time
        start_time = self.get_current_time()
        ## get the time for the next day, as the experiment will start on button click initally but we want to assign every single next boot...
        start_time = start_time + timedelta(days=1)
        ## now for the start time need to reassign the actual hour,min,second for the experimental start
        start_time =  start_time.replace(hour=hr,minute=min,second=sec)
        print("StartUp Time:",start_time)
        start_time_list =[start_time.second,start_time.minute,start_time.hour,start_time.day,self.weekday_conv(datetime.weekday(start_time))]
        year = start_time.year
        month = start_time.month
        ##  # Using datetime.today()  INT
        for count, val in enumerate(range(27,32)):
            # print(val, shutdown_time_list[count],BCDConversion(shutdown_time_list[count]))
            self._bus.write_byte_data(8,val,self.int_to_bcd(start_time_list[count]))
            time.sleep(5)
        if self.bcd_to_int(self.int_to_bcd(self._bus.read_byte_data(8,39))) == 0:
            print("ALARM2 AKA STARTUP: NOT TRIGGERED")
            start_list = []
            for i in range(27,32):
                start_list.append(self.bcd_to_int(self._bus.read_byte_data(8,i)))
            sec,min,hour,days,weekday =  start_list
            print(datetime(year = year+2000, month = month, day=days,hour = hour,minute=min,second=sec))

        elif self.bcd_to_int(self._bus.read_byte_data(8,39)) == 1:
            print("ALARM2 AKA STARTUP: TRIGGERED")
            print("STARTUP Time:\n")
            start_list = []
            for i in range(27,32):
                start_list.append(self.bcd_to_int(self._bus.read_byte_data(8,i)))
            sec,min,hour,days,weekday= start_list
            # Python3 program for the above approach 
            print(datetime(day=days,hour = hour,minute=min,second=sec))

    def startup_curr(self,hr=5,min=0,sec=0):
        """

        hr -> default 5 (5am)

        min -> default 0

        sec -> default 0

        This method sets the startup time registers on the WittyPi 4 mini 
        
        In this case it sets the start up time to be 7am or 9:45pm 
        """
        # SET STARTUP!
        ## get the current time
        start_time = self.get_current_time()
        ## get the time for the next day, as the experiment will start on button click initally but we want to assign every single next boot...
        # start_time = start_time + timedelta(days=1)
        ## now for the start time need to reassign the actual hour,min,second for the experimental start
        start_time =  start_time.replace(hour=hr,minute=min,second=sec)
        print("StartUp Time:",start_time)
        start_time_list =[start_time.second,start_time.minute,start_time.hour,start_time.day,self.weekday_conv(datetime.weekday(start_time))]
        year = start_time.year
        month = start_time.month
        ##  # Using datetime.today()  INT
        for count, val in enumerate(range(27,32)):
            # print(val, shutdown_time_list[count],BCDConversion(shutdown_time_list[count]))
            self._bus.write_byte_data(8,val,self.int_to_bcd(start_time_list[count]))
            time.sleep(5)
        if self.bcd_to_int(self.int_to_bcd(self._bus.read_byte_data(8,39))) == 0:
            print("ALARM2 AKA STARTUP: NOT TRIGGERED")
            start_list = []
            for i in range(27,32):
                start_list.append(self.bcd_to_int(self._bus.read_byte_data(8,i)))
            sec,min,hour,days,weekday =  start_list
            print(datetime(year = year+2000, month = month, day=days,hour = hour,minute=min,second=sec))

        elif self.bcd_to_int(self._bus.read_byte_data(8,39)) == 1:
            print("ALARM2 AKA STARTUP: TRIGGERED")
            print("STARTUP Time:\n")
            start_list = []
            for i in range(27,32):
                start_list.append(self.bcd_to_int(self._bus.read_byte_data(8,i)))
            sec,min,hour,days,weekday= start_list
            # Python3 program for the above approach 
            print(datetime(day=days,hour = hour,minute=min,second=sec))

    def startup_10min(self):
        # SET STARTUP!
        start_time = self.get_current_time() + timedelta(minutes=10)
        start_time_list =[start_time.second,start_time.minute,start_time.hour,start_time.day,self.weekday_conv(datetime.weekday(start_time))]
        year = start_time.year 
        month = start_time.month
        ##  # Using datetime.today()  INT
        for count, val in enumerate(range(27,32)):
            # print(val, shutdown_time_list[count],BCDConversion(shutdown_time_list[count]))
            self._bus.write_byte_data(8,val,self.int_to_bcd(start_time_list[count]))
            time.sleep(5)
        if self.bcd_to_int(self.int_to_bcd(self._bus.read_byte_data(8,39))) == 0:
            print("ALARM2 AKA STARTUP: NOT TRIGGERED")
            start_list = []
            for i in range(27,32):
                start_list.append(self.bcd_to_int(self._bus.read_byte_data(8,i)))
            sec,min,hour,days,weekday =  start_list
            print(datetime(year = year, month = month, day=days,hour = hour,minute=min,second=sec))

        elif self.bcd_to_int(self._bus.read_byte_data(8,39)) == 1:
            print("ALARM2 AKA STARTUP: TRIGGERED")
            print("STARTUP Time:\n")
            start_list = []
            for i in range(27,32):
                start_list.append(self.bcd_to_int(self._bus.read_byte_data(8,i)))
            sec,min,hour,days,weekday= start_list
            # Python3 program for the above approach 
            print(datetime(day=days,hour = hour,minute=min,second=sec))

        
    def shutdown_startup(self,start_1,end_1):
        """
        Performs both a shutdown and then subsequently a startup without closing the SMBus
        start_1 -> 5am (5,0,0)
        start_2 -> 5pm (17,0,0)
        end_1 -> 8am (8,0,0)
        end_2 -> 8pm (20,0,0)

        Based on current time rather than on saved Startup.

        Edge Cases (4 time ranges):
            - Range between start_1 and end_1
            - Range between end_1 and start_2
            - Range between start_2 and end_2
            - Range between end_2 and start_1 (current/next day)
        """
        now = datetime.now()
        
        start_1 = start_1.split(',')
        end_1 = end_1.split(',')
        # print(start_1)
        start_1 = (int(start_1[0]),int(start_1[1]),int(start_1[2]))
        end_1 = (int(end_1[0]),int(end_1[1]),int(end_1[2]))
        year = now.year
        month=now.month
        days = now.day
        print(f"{year}/{month}/{days}")
        
        if now > datetime(year=year,month=month,day=days,hour=start_1[0],minute=start_1[1],second=start_1[2]) and datetime.now() < datetime(year=year,month=month,day=days,hour=end_1[0],minute=end_1[1],second=end_1[2]):  
            # standard operation
            ## SET SHUTDOWN ->  end time
            shutdown_dt = self.get_shutdown_datetime(hr=end_1[0],min=end_1[1],sec=end_1[2])
            ## SET NEXT STARTUP -> (next day)
            self.startup(start_1[0],start_1[1],start_1[2]) # hr,min,sec

        elif now < datetime(year=year,month=month,day=days,hour=start_1[0],minute=start_1[1],second=start_1[2]):
            # early morning setup (before start time)
            ## SET SHUTDOWN -> IMMEDIATELY
            dt_now = now
            shutdown_dt = self.get_shutdown_datetime(hr=dt_now.hour,min=dt_now.minute,sec=dt_now.second)
            ## SET NEXT STARTUP -> (current day)
            self.startup_curr(start_1[0],start_1[1],start_1[2])
        else: 
            # late night setup (time is later than end time)
            ## SET SHUTDOWN -> IMMEDIATELY
            dt_now = now
            shutdown_dt = self.get_shutdown_datetime(hr=dt_now.hour,min=dt_now.minute,sec=dt_now.second)
            ## SET NEXT STARTUP -> (next day)
            self.startup(start_1[0],start_1[1],start_1[2])

        return shutdown_dt
    def get_internal_temperature(self):
        """Acquires temperature data in Celsius"""
        # temperature of wittyPi
        temp = self._bus.read_byte_data(8,50)
        temp_f = temp*(9/5) + 32
        if 'temp' not in self.data_dict.keys():
            time_current_split = str(datetime.now().strftime("%Y%m%d_%H%M%S"))
            self.data_dict['time'] = time_current_split
            self.data_dict['temp'] = [temp]
        ## if key doesn't exist then create
        else:
            time_current_split = str(datetime.now().strftime("%Y%m%d_%H%M%S"))
            self.data_dict['time'].append(time_current_split)
            self.data_dict['temp'].append(temp)
        print(f"Temperature {round(temp,3)} C, {round(temp_f,3)} F")
        return temp
    def append_temp_csv(self):
            """
            Create and or append the temp data to the csv file

            ADD into the CSVfile the image name as well which is going to require a function input...
            """
            if not os.path.exists(self._filename):
                # create the csv with headers..
                with open(self._filename, 'w') as data_file:
                        csv_writer = DictWriter(data_file, fieldnames =self.data_dict.keys())
                        csv_writer.writeheader() # write the header...
            with open(self._filename, 'a') as data_file:
                try:
                    # Try to pass the dictionary into the csv 
                    csv_writer = DictWriter(data_file, fieldnames =self.data_dict.keys())
                    #print(self.data_dict.values())
                    # first got the length of the list...
                    len_list = len(list(self.data_dict.values())[0])
                    # looping over each time instance:
                    for t in range(len_list):
                        row_data = {}
                        for k in self.data_dict.keys():
                            # add data at this time for sensor 'k' to dictionary
                            row_data[k] = self.data_dict[k][t]
                        # write this row...of data for the timestep...
                        # before the next time instance write what we have to csv
                        csv_writer.writerow(row_data) # appends data to the headers
                    # reset the data_dict
                    for k in self.data_dict:
                        self.data_dict[k] = []
                except Exception as e:
                    print(f"An error occurred while appending to the CSV file: {e}")

class Sensor:
    data_dict = {"name": [], "time": []}
    def __init__(self, device=None, i2c=None):
         self.i2c = i2c if i2c is not None else board.I2C()
         self.sensor_device = device

    def get_data(self,sensor_type):
        """
        Depending on the child class sensor device get_data will be
        used in order to grab the current sensor reading from the sensor.
        """
        data = getattr(self.sensor_device,sensor_type) # object, attribute
        return data

    def add_data(self,sensor_type):
        """
        Add data into the dictionary under the key of the sensor type

        Also returns the current data that was recieved in case that wants to be examined
        """
        data = self.get_data(sensor_type)
        ## check to see if the key exists first and if it does then add to it
        self.data_dict.setdefault(sensor_type, []).append(data)
        return data

    def display(self):
        """
        Display the sensor dictionary
        """
        print("Sensor Data")
        d = self.data_dict
        print(d)

    def sensor_deinit(self):
        self.i2c.deinit() 

class TempRHSensor(Sensor):
    def __init__(self, i2c=None):
        super().__init__(adafruit_sht31d.SHT31D(i2c if i2c else board.I2C()), i2c)


        self.sensor_types = ['temperature','relative_humidity']
    def temp_rh_data(self):
        data1 = self.add_data(self.sensor_types[0])
        data2 = self.add_data(self.sensor_types[1])


        return data1,data2

class PresSensor(Sensor):
    def __init__(self, i2c=None):
        super().__init__(adafruit_bmp3xx.BMP3XX_I2C(i2c if i2c else board.I2C()), i2c)
        
        self.sensor_types = ['pressure']
    def pressure_data(self):
        data1 = self.add_data(self.sensor_types[0])
        return data1

def map_range(value, in_min, in_max, out_min, out_max):
    return out_min + (value - in_min) * (out_max - out_min) / (in_max - in_min)

def adc_to_wind_speed(val):
    """Convert MCP3421 18-bit ADC value to wind speed in m/s with offset correction."""
    voltage_val = (val / 131072) * 2.048  # Convert ADC reading to voltage
    corrected_voltage = max(voltage_val - 0.0053, 0.4)  # Shift zero point
    return (corrected_voltage - 0.4) * (32.4 / (2.0 - 0.4))  # Linear mapping

class WindSensor(Sensor):
    def __init__(self, i2c=None):
        super().__init__(i2c=i2c)
        self.adc = ADC.MCP3421(self.i2c, gain=1, resolution=18, continuous_mode=True)
        self.adc_channel = AnalogIn(self.adc)

    def get_data(self, sensor_type="wind_speed"):
        adc_val = self.adc_channel.value
        return adc_to_wind_speed(adc_val)

    def add_data(self, sensor_type="wind_speed"):
        data = self.get_data(sensor_type)
        self.data_dict.setdefault(sensor_type, []).append(data) # Add to dictionary
        return data

class Display:
    """
    Display info and status
    """
    def __init__(self, i2c=None):
        self.width = 128
        self.height = 64
        self.font = ImageFont.load_default()
        self.enabled = True  # Initialize as True, will be set to False on error
        self.ip = self.get_ip_address()
        self._i2c = i2c if i2c is not None else board.I2C()
        try:
            self._disp = adafruit_ssd1306.SSD1306_I2C(self.width,self.height, self._i2c)
            self._disp.width = self.width
            self._disp.height = self.height
            self._disp.fill(0)
            self._disp.show()
        except RuntimeError as e:
            print(f'Display: {e}', file=sys.stderr)
            self.enabled = False


    def display_sensor_data(self, temperature, humidity, pressure, wind_speed):
        if not self.enabled:
            return

        msg = [
            time.strftime('%Y-%m-%d      %H:%M:%S'),
            f'Temp: {temperature:.1f} C',
            f'Humidity: {humidity:.1f} %',
            f'Pressure: {pressure:.1f} hPa',
            f'Wind: {wind_speed:.1f} m/s'
        ]
        
        image = Image.new('1', (self.width, self.height))
        draw = ImageDraw.Draw(image)
        
        draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)

        x, y = 0, 0
        for item in msg:
            draw.text((x, y), item, font=self.font, fill=255)
            y += 12 

        self._disp.image(image)
        self._disp.show()

    def display_msg(self, status, img_count=1):
        if not self.enabled:
            return

        msg = [f"{time.strftime('%Y-%m-%d      %H:%M:%S')}",
                f'{status}',
                f'IP: {self.ip}'
                ]

        image = Image.new('1', (self.width, self.height))
        draw = ImageDraw.Draw(image)
        
        draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        x, y = 0, 0
        for item in msg:
            draw.text((x, y), item, font=self.font, fill=255)
            y += 14
        
        self._disp.image(image)
        self._disp.show()

    def clear_display(self):
        if not self.enabled:
            return
        image = Image.new('1', (self.width, self.height))
        self._disp.image(image)
        self._disp.show()

    def get_ip_address(self, interface="eth0"):
        """
        Get the local IP address of a specific network interface (default: eth0).
        Falls back to wlan0 if eth0 is unavailable.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ip_addr = fcntl.ioctl(
                s.fileno(),
                0x8915,  # SIOCGIFADDR (Get interface address)
                struct.pack('256s', bytes(interface[:15], "utf-8"))
            )[20:24]

            return f"{socket.inet_ntoa(ip_addr)}"

        except OSError:
            if interface == "eth0":
                return self.get_ip_address("wlan0")  # Try Wi-Fi if Ethernet fails
            return "Unknown"  # No network connection

    def disp_deinit(self):
        self._i2c.deinit()

class MultiSensor(Sensor):
    """
    Class that holds the various different sensors for acquiring data
    """
    def __init__(self, path_sensors, i2c=None):
        """
        Initialize the different sensor classes
        """
        super().__init__(i2c=i2c)
        self.unit_name = name
        self._temp_rh = TempRHSensor(i2c=i2c)
        self._pres = PresSensor(i2c=i2c)
        self._ws = WindSensor(i2c=i2c)

        with WittyPi() as witty:
            self._shutdown_dt = witty.get_shutdown_datetime() 

        start_time= datetime.now().strftime('%Y%m%d_%H%M%S')
        self.filename = f'{path_sensors}.csv'# all data is written to this CSV...

        self.latest_readings = {
            "temperature": None, "relative_humidity": None,
            "pressure": None, "wind_speed": None
        }

    # def get_shutdown_datetime(self):
    #     return self._shutdown_dt

    def add_data(self,date_time):
        """
        Collect sensor data, store it in the dictionary, and update latest readings.
        """
        # check that time is in proper range based on wittyPi set shutdown time
        if self._shutdown_dt >= date_time:
            time_current_split = str(date_time.strftime("%Y%m%d_%H%M%S"))
            self.data_dict['time'].append(time_current_split)
            self.data_dict["name"].append(self.unit_name)

            ## Add Temperature and Humidity
            self.latest_readings["temperature"], self.latest_readings["relative_humidity"] = self._temp_rh.temp_rh_data()
            self.latest_readings["pressure"] = self._pres.pressure_data()
            self.latest_readings["wind_speed"] = self._ws.add_data()
        else:
            raise ShutdownTime

    def append_to_csv(self):
        """
        Write collected sensor data to CSV file.
        """
        if not os.path.exists(self.filename):  # create the csv with headers..
            with open(self.filename, 'w') as data_file:
                    csv_writer = DictWriter(data_file, fieldnames =self.data_dict.keys())
                    csv_writer.writeheader()

        with open(self.filename, 'a') as data_file:
            try: # Try to pass the dictionary into the csv 
                csv_writer = DictWriter(data_file, fieldnames =self.data_dict.keys())
                rows = []
                print(self.data_dict)
                len_list = len(next(iter(self.data_dict.values())))
                for t in range(len_list):
                    rows.append({k: self.data_dict[k][t] for k in self.data_dict.keys()})
                csv_writer.writerows(rows)
            
                for k in self.data_dict: # reset data_dict keys
                    self.data_dict[k] = []

                print("~*csv updated*~")

            except Exception as e:
                print(f"An error occurred while appending to the CSV file: {e}")

    def sensors_deinit(self):
        print("Deinitializing I2C Bus")
        self._temp_rh.sensor_deinit()
        self._pres.sensor_deinit()
        self._ws.sensor_deinit()
        # self._disp.sensor_deinit()
        print("Finished Denitializing I2C Bus...Reading for Reboot")

if __name__ == "__main__":
    print("Starting Sensor Monitoring...")

    shared_i2c = board.I2C()
    sensors = MultiSensor(path_sensors="/home/pi/data/", i2c=shared_i2c)
    display = Display(i2c=shared_i2c)

    start_time = time.time()  # Initialize start_time before entering the loop

    try:
        while True:
            time.sleep(2)  # Sample interval
            time_current = datetime.now()

            # Get sensor readings
            sensors.add_data(time_current)
            temp = sensors._temp_rh.get_data('temperature')
            humidity = sensors._temp_rh.get_data('relative_humidity')
            pressure = sensors._pres.get_data('pressure')
            wind_speed = sensors._ws.get_data()

            # Display readings on OLED screen
            display.display_sensor_data(temp, humidity, pressure, wind_speed)

            # Save to CSV every 10 seconds
            if (time.time() - start_time) >= 10:
                sensors.append_to_csv()
                start_time = time.time()  # Reset timer

    except KeyboardInterrupt:
        print("Exiting Program...")
        display.clear_display()
        sensors.sensors_deinit()

