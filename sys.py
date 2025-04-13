import RPi.GPIO as GPIO
import time
import os

BUTTON_PIN = 3  # GPIO3 (pin 5)

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN)

def shutdown(channel):
    print("Shutdown button pressed!")
    #os.system("sudo shutdown now")

GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=shutdown, bouncetime=2000)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()
