import board
import busio
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
import time
import neopixel
import requests

i2c = busio.I2C(board.SCL, board.SDA)
pn532 = PN532_I2C(i2c, debug=False)

LED_PIN = board.D18  # GPIO pin you're using
LED_COUNT = 24  # Set the number of LEDs
pixels = neopixel.NeoPixel(LED_PIN, LED_COUNT, auto_write=False)


# Get firmware version
ic, ver, rev, support = pn532.firmware_version
print(f'Found PN532 with firmware version: {ver}.{rev}')

# Configure to read MiFare cards
pn532.SAM_configuration()

def offled():
    pixels.fill((0, 0, 0))  # Turn off LEDs
    pixels.show()
    

# Function to parse the color string (e.g., '000200000' -> (0, 2, 0))
def parse_color(color_str):
    # Extract RGB components from the color string
    red = int(color_str[:3])
    green = int(color_str[3:6])
    blue = int(color_str[6:])
    return (red, green, blue)
    
    
def spinner_animation(duration=1.0, wait=0.01):
    """Show a spinner that runs around the LED ring."""
    start_time = time.time()
    while (time.time() - start_time) < duration:
        for i in range(LED_COUNT):
            pixels.fill((0, 0, 0))  # Turn off all
            pixels[i] = (0, 255, 0)  # Bright green dot
            pixels.show()
            time.sleep(wait)
    offled()
    

    
# Function to control the LED based on server response
def control(color_str, duration_ms):
    print("Controlling LED with color:", color_str)
    
    # Parse the color string into a tuple of RGB values
    color = parse_color(color_str)

    # Convert the duration from milliseconds to seconds
    duration = duration_ms / 1000.0  # Convert to seconds

    # Set the color of the LEDs
    for i in range(LED_COUNT):
        pixels[i] = color
    pixels.show()

    # Wait for the specified duration and turn off the LEDs
    time.sleep(duration)
    pixels.fill((0, 0, 0))  # Turn off LEDs
    pixels.show()


# Function to handle tapping the card
def tap(card):
    url = "http://127.0.0.1:8000/tap"  # Your server URL
    #url = "http://192.168.100.41:8000/tap"  # Your server URL

    # Sending the card data to the server
    data = {"device": "Entrance", "card": str(card)}

    res = requests.post(url, json=data)

    if res.status_code == 200:
        data = res.json()
        print("Server Response:", data)
        
        # Extract color, duration, and other parameters from the response
        color_str = data.get("color", "000000000")  # Default to black if no color is provided
        duration_ms = data.get("duration", 1000)  # Default to 1 second if no duration is provided

        # Call the control function with the extracted data
        control(color_str, duration_ms)
    else:
        print("Error:", res.status_code, res.text)



# --- Run Boot Animation ---
spinner_animation()

print('Waiting for NFC card...')
while True:
    uid = pn532.read_passive_target(timeout=0.5)
    if uid is not None:
        id =uid.hex()
        print(id)
        tap(id)
