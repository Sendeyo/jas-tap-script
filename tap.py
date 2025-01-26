import time
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import requests
import board
import neopixel

print("Script started")
# Initialize the RFID reader
reader = SimpleMFRC522()

# Setup for LED
LED_PIN = board.D18  # GPIO pin you're using
LED_COUNT = 24  # Set the number of LEDs
pixels = neopixel.NeoPixel(LED_PIN, LED_COUNT, auto_write=False)

# Function to parse the color string (e.g., '000200000' -> (0, 2, 0))
def parse_color(color_str):
    # Extract RGB components from the color string
    red = int(color_str[:3])
    green = int(color_str[3:6])
    blue = int(color_str[6:])
    return (red, green, blue)

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
    url = "http://192.168.100.36:8000/tap"  # Your server URL

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

# Function to handle the reading of the RFID card
def read(id):
    print("Card ID:", id)
    tap(id)
    time.sleep(0.2)

try:
    while True:
        # Read the RFID card
        id, text = reader.read()
        read(id)

finally:
    # Cleanup GPIO settings
    GPIO.cleanup()
