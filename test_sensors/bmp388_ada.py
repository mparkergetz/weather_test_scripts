import time
import board
import adafruit_bmp3xx
i2c = board.I2C()
bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c)

print("Pressure: {:6.1f} hPa".format(bmp.pressure))
print("Temperature: {:5.2f} C".format(bmp.temperature))
