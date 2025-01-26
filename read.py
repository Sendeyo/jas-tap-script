import time
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import requests


reader = SimpleMFRC522()


def control(color, duration, brightness):
    pass


def tap(card):
    url = "http://127.0.0.1:8000/tap"

    data = {"device": "Entrance", "card":str(card)}
    
    try:
        res = requests.post(url, json=data)
    except Exception as e:
        print(e)
        return e

    if res.status_code == 200:
        data = res.json()
        print(data)
        control(data)
    else:
        print("Error:", res.status_code, res.text)

def read(id):
    print(id)
    tap(id)
    time.sleep(0.2)

try:
    while True:
        id, text = reader.read()
        read(id)
    
finally:
    GPIO.cleanup()