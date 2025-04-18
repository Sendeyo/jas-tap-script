import board
import busio
import time
import logging
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
import neopixel
import requests
from requests.exceptions import RequestException
import threading
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from datetime import datetime

# Configuration
CONFIG = {
    'LED_PIN': board.D18,
    'LED_COUNT': 24,
    'SERVER_URL': 'http://127.0.0.1:8000',
    'DEVICE_NAME': 'Entrance',
    'REQUEST_TIMEOUT': 5,  # seconds
    'BATTERY_CHECK_INTERVAL': 60,  # Check battery every 60 seconds
    'ADC_GAIN': 1,  # ADS1115 gain (1 = +/-4.096V)
    'BATTERY_ADC_CHANNEL': 0,  # Channel on ADS1115
    'BATTERY_MIN_VOLTAGE': 3.0,  # Fully discharged
    'BATTERY_MAX_VOLTAGE': 4.2,  # Fully charged
    'BATTERY_WARNING_VOLTAGE': 3.3,  # Warn when below this
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NFCBatteryDevice:
    def __init__(self):
        # Initialize I2C bus
        self.i2c = busio.I2C(board.SCL, board.SDA)
        
        # Initialize NFC reader
        self._init_nfc()
        
        # Initialize battery monitor
        self._init_battery()
        
        # Initialize LEDs
        self._init_leds()
        
        # Start battery monitoring thread
        self.battery_monitor_active = True
        self.battery_thread = threading.Thread(target=self._battery_monitor)
        self.battery_thread.daemon = True
        self.battery_thread.start()

    def _init_nfc(self):
        """Initialize PN532 NFC reader"""
        self.pn532 = PN532_I2C(self.i2c, debug=False)
        ic, ver, rev, support = self.pn532.firmware_version
        logger.info(f'Found PN532 with firmware version: {ver}.{rev}')
        self.pn532.SAM_configuration()

    def _init_battery(self):
        """Initialize ADS1115 battery monitor"""
        self.ads = ADS.ADS1115(self.i2c, gain=CONFIG['ADC_GAIN'])
        self.battery_channel = AnalogIn(self.ads, ADS.P0)
        logger.info("Battery monitor initialized")

    def _init_leds(self):
        """Initialize NeoPixel LEDs"""
        self.pixels = neopixel.NeoPixel(
            CONFIG['LED_PIN'],
            CONFIG['LED_COUNT'],
            auto_write=False
        )
        logger.info("LEDs initialized")
        self.spinner_animation(color="255255255")  # Boot animation

    def spinner_animation(self, duration=1.0, wait=0.01, color="000000255"):
        """Show a spinner animation"""
        start_time = time.time()
        color_rgb = self.parse_color(color)
        
        while (time.time() - start_time) < duration:
            for i in range(CONFIG['LED_COUNT']):
                self.pixels.fill((0, 0, 0))
                self.pixels[i] = color_rgb
                self.pixels.show()
                time.sleep(wait)
        self.off_led()

    def off_led(self):
        """Turn off all LEDs"""
        self.pixels.fill((0, 0, 0))
        self.pixels.show()

    def parse_color(self, color_str):
        """Parse color string into RGB tuple"""
        try:
            red = int(color_str[:3])
            green = int(color_str[3:6])
            blue = int(color_str[6:])
            return (red, green, blue)
        except (ValueError, IndexError):
            logger.error(f"Invalid color string: {color_str}")
            return (0, 0, 0)

    def control_led(self, color_str, duration_ms):
        """Control LED with specified color and duration"""
        color = self.parse_color(color_str)
        duration = duration_ms / 1000.0
        
        self.pixels.fill(color)
        self.pixels.show()
        time.sleep(duration)
        self.off_led()

    def _read_battery(self):
        """Read battery voltage and percentage"""
        try:
            voltage = self.battery_channel.voltage
            percentage = int((voltage - CONFIG['BATTERY_MIN_VOLTAGE']) / 
                           (CONFIG['BATTERY_MAX_VOLTAGE'] - CONFIG['BATTERY_MIN_VOLTAGE']) * 100)
            percentage = max(0, min(100, percentage))
            return voltage, percentage
        except Exception as e:
            logger.error(f"Error reading battery: {str(e)}")
            return None, None

    def _send_battery_status(self, percentage):
        """Send battery status to server"""
        try:
            url = f"{CONFIG['SERVER_URL']}/battery/{percentage}"
            response = requests.get(url, timeout=CONFIG['REQUEST_TIMEOUT'])
            response.raise_for_status()
            logger.info(f"Battery status sent: {percentage}%")
            return True
        except RequestException as e:
            logger.error(f"Failed to send battery status: {str(e)}")
            return False

    def _battery_monitor(self):
        """Continuous battery monitoring thread"""
        while self.battery_monitor_active:
            voltage, percentage = self._read_battery()
            if percentage is not None:
                self._send_battery_status(percentage)
                if voltage < CONFIG['BATTERY_WARNING_VOLTAGE']:
                    self._low_battery_warning()
            
            # Wait for next check
            for _ in range(CONFIG['BATTERY_CHECK_INTERVAL']):
                if not self.battery_monitor_active:
                    return
                time.sleep(1)

    def _low_battery_warning(self):
        """Visual warning for low battery"""
        for _ in range(3):
            self.pixels.fill((255, 50, 0))  # Orange color
            self.pixels.show()
            time.sleep(0.5)
            self.off_led()
            time.sleep(0.5)

    def handle_nfc_tap(self, card_uid):
        """Handle NFC card tap event"""
        url = f"{CONFIG['SERVER_URL']}/tap"
        data = {"device": CONFIG['DEVICE_NAME'], "card": card_uid}
        
        try:
            response = requests.post(
                url,
                json=data,
                timeout=CONFIG['REQUEST_TIMEOUT']
            )
            response.raise_for_status()
            
            response_data = response.json()
            color_str = response_data.get("color", "000000000")
            duration_ms = response_data.get("duration", 1000)
            
            self.control_led(color_str, duration_ms)
            return True
            
        except RequestException as e:
            logger.error(f"Server communication failed: {str(e)}")
            self.control_led("255000000", 500)  # Red flash for error
            return False

    def run(self):
        """Main run loop"""
        logger.info("Waiting for NFC cards...")
        while True:
            # Check for NFC cards
            uid = self.pn532.read_passive_target(timeout=0.5)
            if uid is not None:
                card_id = uid.hex()
                logger.info(f"Card detected: {card_id}")
                self.handle_nfc_tap(card_id)
            
            time.sleep(0.1)  # Small delay to prevent CPU overload

    def cleanup(self):
        """Clean up resources"""
        self.battery_monitor_active = False
        self.battery_thread.join()
        self.off_led()
        logger.info("Device shutdown complete")

if __name__ == "__main__":
    device = None
    try:
        device = NFCBatteryDevice()
        device.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if device:
            device.cleanup()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        if device:
            device.cleanup()
        raise