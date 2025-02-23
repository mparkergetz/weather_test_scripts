import smbus2
import time

SHT30_I2C_ADDR = 0x44  # Default I2C address
CMD_MEASURE = [0x2C, 0x06]  # High repeatability measurement command

def read_sht30():
    bus = smbus2.SMBus(1)  # Use I2C bus 1
    bus.write_i2c_block_data(SHT30_I2C_ADDR, CMD_MEASURE[0], CMD_MEASURE[1:])

    time.sleep(0.5)  # Wait for measurement

    data = bus.read_i2c_block_data(SHT30_I2C_ADDR, 0, 6)
    bus.close()

    temp_raw = data[0] << 8 | data[1]
    humidity_raw = data[3] << 8 | data[4]

    temperature = -45 + (175 * temp_raw / 65535.0)
    humidity = 100 * humidity_raw / 65535.0

    return temperature, humidity

while True:
    temp, hum = read_sht30()
    print(f"Temperature: {temp:.2f}°C, Humidity: {hum:.2f}%")
    time.sleep(2)
