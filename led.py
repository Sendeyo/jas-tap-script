import time
import board
import neopixel

LED_PIN = board.D18  # GPIO pin you're using
LED_COUNT = 24  # Set the number of LEDs

# Create the NeoPixel object
pixels = neopixel.NeoPixel(LED_PIN, LED_COUNT, auto_write=False)

# Function to change colors
def change_color(color):
    for i in range(LED_COUNT):
        pixels[i] = color
    pixels.show()

# Continuously cycle through colors
while True:
    change_color((255, 0, 0))  # Red
    time.sleep(1)  # Wait for 1 second
    change_color((0, 255, 0))  # Green
    time.sleep(1)  # Wait for 1 second
    change_color((0, 0, 255))  # Blue
    time.sleep(1)  # Wait for 1 second
