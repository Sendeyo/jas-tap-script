import board
import busio
import time
import logging
import threading
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
import neopixel
import requests
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    'LED_PIN': board.D18,
    'LED_COUNT': 24,
    'SERVER_URL': 'http://127.0.0.1:8000',
    'DEVICE_NAME': 'Entrance',
    'REQUEST_TIMEOUT': 5,
    'BATTERY_CHECK_INTERVAL': 10,
    'ADC_GAIN': 1,
    'BATTERY_MIN_VOLTAGE': 3.0,
    'BATTERY_MAX_VOLTAGE': 4.1,
    'BATTERY_WARNING_VOLTAGE': 3.3,
    'PN532_RESET_PIN': board.D4,
}

class DeviceController:
    def __init__(self):
        # Initialize LED hardware first
        self.pixels = neopixel.NeoPixel(
            CONFIG['LED_PIN'],
            CONFIG['LED_COUNT'],
            auto_write=False
        )
        
        # Now we can call LED methods
        self.off_led()  # Turn off LEDs initially
        
        # Show startup animation
        self.spinner_animation(color="000000255", duration=0.5)
        
        # Initialize I2C bus
        self.i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
        
        # Initialize battery monitor
        self._init_battery()
        voltage, percentage = self._read_battery()
        logger.info(f"Initial battery: {voltage:.2f}V ({percentage}%)")
        self._show_battery_level(percentage)
        
        # Initialize NFC
        self._init_nfc()
        
        # Start battery monitoring thread
        self.battery_monitor_active = True
        self.battery_thread = threading.Thread(target=self._battery_monitor)
        self.battery_thread.daemon = True
        self.battery_thread.start()

        # System ready
        self.spinner_animation(color="000255000", duration=0.5)
        logger.info("System initialized")

    # LED Control Methods (defined first)
    def off_led(self):
        """Turn off all LEDs."""
        self.pixels.fill((0, 0, 0))
        self.pixels.show()
        
    def parse_color(self, color_str):
        """Parse color string into RGB tuple."""
        try:
            red = int(color_str[:3])
            green = int(color_str[3:6])
            blue = int(color_str[6:])
            return (red, green, blue)
        except (ValueError, IndexError):
            logger.error(f"Invalid color string: {color_str}")
            return (0, 0, 0)
    
    def spinner_animation(self, duration=1.0, wait=0.01, color="000000255"):
        """Show a spinner animation."""
        start_time = time.time()
        color_rgb = self.parse_color(color)
        while (time.time() - start_time) < duration:
            for i in range(CONFIG['LED_COUNT']):
                self.pixels.fill((0, 0, 0))
                self.pixels[i] = color_rgb
                self.pixels.show()
                time.sleep(wait)
        self.off_led()
    
    def control_led(self, color_str, duration_ms):
        """Control LED with specified color and duration."""
        color = self.parse_color(color_str)
        duration = duration_ms / 1000.0
        self.pixels.fill(color)
        self.pixels.show()
        time.sleep(duration)
        self.off_led()

    def _show_battery_level(self, percentage):
        """Visual indication of battery level"""
        if percentage > 60:
            color = (0, 255, 0)  # Green
        elif percentage > 30:
            color = (255, 255, 0)  # Yellow
        else:
            color = (255, 0, 0)  # Red
            
        lit_leds = int(CONFIG['LED_COUNT'] * percentage / 100)
        self.pixels.fill((0, 0, 0))
        for i in range(lit_leds):
            self.pixels[i] = color
        self.pixels.show()
        time.sleep(2)
        self.off_led()

    # Battery Monitoring Methods
    def _init_battery(self):
        """Initialize ADS1115 battery monitor"""
        for attempt in range(3):
            try:
                self.ads = ADS.ADS1115(self.i2c, gain=CONFIG['ADC_GAIN'])
                self.battery_channel = AnalogIn(self.ads, ADS.P0)
                _ = self.battery_channel.voltage  # Test read
                return
            except Exception as e:
                if attempt == 2:
                    logger.error("Battery monitor init failed")
                    raise
                time.sleep(0.5)

    def _read_battery(self):
        """Read battery voltage and percentage"""
        try:
            voltage = self.battery_channel.voltage
            percentage = int((voltage - CONFIG['BATTERY_MIN_VOLTAGE']) / 
                         (CONFIG['BATTERY_MAX_VOLTAGE'] - CONFIG['BATTERY_MIN_VOLTAGE']) * 100)
            percentage = max(0, min(100, percentage))
            return voltage, percentage
        except Exception as e:
            logger.error(f"Battery read error: {str(e)}")
            return None, None

    def _send_battery_status(self, percentage):
        """Send battery percentage to server"""
        try:
            url = f"{CONFIG['SERVER_URL']}/battery/{percentage}"
            response = requests.get(url, timeout=CONFIG['REQUEST_TIMEOUT'])
            response.raise_for_status()
            logger.info(f"Battery status sent: {percentage}%")
            return True
        except RequestException as e:
            logger.error(f"Failed to send battery status: {str(e)}")
            return False

    def _low_battery_warning(self):
        """Visual low battery alert"""
        for _ in range(3):
            self.pixels.fill((255, 50, 0))  # Orange
            self.pixels.show()
            time.sleep(0.5)
            self.off_led()
            time.sleep(0.5)

    def _battery_monitor(self):
        """Background battery monitoring thread"""
        # Send initial reading immediately
        voltage, percentage = self._read_battery()
        if percentage is not None:
            self._send_battery_status(percentage)
            if voltage < CONFIG['BATTERY_WARNING_VOLTAGE']:
                self._low_battery_warning()
        
        # Regular monitoring loop
        while self.battery_monitor_active:
            voltage, percentage = self._read_battery()
            if percentage is not None:
                self._send_battery_status(percentage)
                if voltage < CONFIG['BATTERY_WARNING_VOLTAGE']:
                    self._low_battery_warning()
            
            for _ in range(CONFIG['BATTERY_CHECK_INTERVAL']):
                if not self.battery_monitor_active:
                    return
                time.sleep(1)

    # NFC Methods
    def _init_nfc(self):
        """Initialize PN532 NFC reader"""
        self.spinner_animation(color="255255000", duration=0.3)  # Yellow
        
        reset_pin = DigitalInOut(CONFIG['PN532_RESET_PIN'])
        reset_pin.switch_to_output(value=False)
        time.sleep(0.1)
        reset_pin.value = True
        time.sleep(0.5)
        
        try:
            self.pn532 = PN532_I2C(self.i2c, reset=reset_pin, debug=False)
            
            for attempt in range(3):
                try:
                    ic, ver, rev, support = self.pn532.firmware_version
                    logger.info(f'PN532 v{ver}.{rev} initialized')
                    self.pn532.SAM_configuration()
                    self.spinner_animation(color="000255000", duration=0.2)
                    return
                except RuntimeError as e:
                    if attempt == 2:
                        raise
                    time.sleep(0.5)
        except Exception as e:
            logger.error(f"NFC init failed: {str(e)}")
            self.control_led("255000000", 1000)
            raise

    def handle_card_tap(self, card_uid):
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
            logger.info(f"Server response: {response_data}")
            
            color_str = response_data.get("color", "000000000")
            duration_ms = response_data.get("duration", 1000)
            
            self.control_led(color_str, duration_ms)
            
        except RequestException as e:
            logger.error(f"Server communication failed: {str(e)}")
            self.control_led("255000000", 500)

    def run(self):
        """Main run loop"""
        logger.info("Waiting for NFC cards...")
        while True:
            uid = self.pn532.read_passive_target(timeout=0.5)
            if uid is not None:
                card_id = uid.hex()
                logger.info(f"Card detected: {card_id}")
                self.handle_card_tap(card_id)
            time.sleep(0.1)

    def cleanup(self):
        """Clean up resources"""
        self.battery_monitor_active = False
        if hasattr(self, 'battery_thread') and self.battery_thread.is_alive():
            self.battery_thread.join()
        self.off_led()
        logger.info("Device shutdown complete")

if __name__ == "__main__":
    controller = None
    try:
        controller = DeviceController()
        controller.run()
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        if controller:
            controller.cleanup()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        if controller:
            controller.cleanup()
        raise