import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from datetime import datetime

# Initialize I2C and ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
ads.gain = 1  # +/-4.096V (perfect for 1S LiPo)
chan = AnalogIn(ads, ADS.P0)  # Connect battery to A0

# Battery parameters (for 1S LiPo)
MIN_VOLTAGE = 3.0  # Fully discharged
MAX_VOLTAGE = 4.2  # Fully charged

def read_voltage(samples=5, delay=0.1):
    """Read voltage with simple averaging"""
    readings = []
    for _ in range(samples):
        readings.append(chan.voltage)
        time.sleep(delay)
    return sum(readings) / samples

def voltage_to_percentage(voltage):
    """Convert voltage to battery percentage (returns integer)"""
    percentage = (voltage - MIN_VOLTAGE) / (MAX_VOLTAGE - MIN_VOLTAGE) * 100
    return int(max(0, min(100, percentage)))  # Clamp between 0-100 and convert to int

try:
    while True:
        # Get timestamp
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Read voltage and percentage
        voltage = read_voltage()
        percentage = voltage_to_percentage(voltage)
        
        # Print results (percentage as integer)
        print(f"{now} - Voltage: {voltage:.2f}V, Charge: {percentage}%")
        
        # Wait before next reading
        time.sleep(5)

except KeyboardInterrupt:
    print("\nMonitoring stopped")
