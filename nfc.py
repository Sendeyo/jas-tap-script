import board
import busio
import time
import logging
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
import neopixel
import requests
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
    'SERVER_URL': 'http://127.0.0.1:8000/tap',
    'DEVICE_NAME': 'Entrance',
    'REQUEST_TIMEOUT': 5,  # seconds
}

class NFCRingController:
    def __init__(self):
        # Initialize hardware
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pn532 = PN532_I2C(self.i2c, debug=False)
        self.pixels = neopixel.NeoPixel(
            CONFIG['LED_PIN'], 
            CONFIG['LED_COUNT'], 
            auto_write=False
        )
        
        # Verify PN532
        ic, ver, rev, support = self.pn532.firmware_version
        logger.info(f'Found PN532 with firmware version: {ver}.{rev}')
        self.pn532.SAM_configuration()
        
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
            return (0, 0, 0)  # Default to off
    
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
    
    def handle_card_tap(self, card_uid):
        """Handle NFC card tap event."""
        data = {
            "device": CONFIG['DEVICE_NAME'], 
            "card": card_uid
        }
        
        try:
            response = requests.post(
                CONFIG['SERVER_URL'],
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
            # Visual error feedback
            self.control_led("255000000", 500)  # Red flash for error
    
    def run(self):
        """Main run loop."""
        logger.info("Waiting for NFC card...")
        self.spinner_animation(color="255255255")  # Boot animation
        
        while True:
            uid = self.pn532.read_passive_target(timeout=0.5)
            if uid is not None:
                card_id = uid.hex()
                logger.info(f"Card detected: {card_id}")
                self.handle_card_tap(card_id)

if __name__ == "__main__":
    controller = NFCRingController()
    controller.run()