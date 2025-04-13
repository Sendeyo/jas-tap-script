import board
import neopixel
import time

pixels = neopixel.NeoPixel(board.D18, 24, auto_write=True)
pixels.fill((20, 20, 20))  # Full red

time.sleep(3)
pixels.fill((0, 0, 0))  # Turn off LEDs
pixels.show()