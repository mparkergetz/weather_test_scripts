import sys
import time
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import socket
import os
import board

class Display:
    def __init__(self):
        self.width = 128
        self.height = 64
        self.font = ImageFont.load_default()
        self.enabled = True  # Initialize as True, will be set to False on error
        self.ip = self.get_ip_address()
        i2c = board.I2C()
        try:
            self._disp = adafruit_ssd1306.SSD1306_I2C(self.width,self.height, i2c)
            self._disp.width = self.width
            self._disp.height = self.height
            # self.disp.begin()
            self._disp.fill(0)
            # self.disp.clear()
            self._disp.show()
        except RuntimeError as e:
            print(f'Display: {e}', file=sys.stderr)
            self.enabled = False

    def display_time(self):
        if not self.enabled:
            return

        image = Image.new('1', (self.width, self.height))
        draw = ImageDraw.Draw(image)
        
        # Clear the image buffer
        draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)

        # Get the current time
        current_time = time.strftime('%H:%M:%S')
        
        # Draw the time on the image
        draw.text((0, 1), current_time, font=self.font, fill=255)

        # Display the image
        self._disp.image(image)
        self._disp.show()

    def display_msg(self, status):
        if not self.enabled:
            return

        msg = [time.strftime('%H:%M:%S'),
                f'{status}',
                f'IP: {self.ip}']

        
        image = Image.new('1', (self.width, self.height))
        draw = ImageDraw.Draw(image)
        
        # Clear the image buffer
        draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        #_, font_height = self.font.getsize('Sample Text')
        x, y = 0, 0
        for item in msg:
            draw.text((x, y), item, font=self.font, fill=255)
            y += 14
        
        self._disp.image(image)
        self._disp.show()

    def display_weather(self, temp=None, humid=None, pres=None, wind=None):
        if not self.enabled:
            return

        msg = [time.strftime('%H:%M:%S'),
                f'Temp: {temp} C   Humid: {humid}%',
                f'Pres: {pres} kPa, Wind: {wind} m/s',
                f'IP: {self.ip}']

        
        image = Image.new('1', (self.width, self.height))
        draw = ImageDraw.Draw(image)
        
        # Clear the image buffer
        draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        #_, font_height = self.font.getsize('Sample Text')
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


    def get_ip_address(self):
        try:
            hostname = socket.gethostname()
            result = os.popen(f"ifconfig eth0").read()
            IPAddr = result.split("inet ")[1].split()[0]
            return f'{IPAddr}'
        except:
            return "Unknown"


if __name__ == '__main__':
    disp = Display()
    ip = disp.get_ip_address()

    try:
        while True:
            msg = 'Test'
                  # time.strftime('%H:%M:%S'),
                  # f'IP: {ip}'
            disp.display_weather()
            current_second_fraction = time.time() % 1
            sleep_duration = 1 - current_second_fraction
            time.sleep(sleep_duration)
    except KeyboardInterrupt:
        disp.clear_display()

    finally:
        disp.clear_display()
