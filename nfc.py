import board
import busio
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
import time
import neopixel
import requests

#Script part
import subprocess
import socket
import os

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
    
    
def spinner_animation(duration=1.0, wait=0.01, color="000000255"):
    """Show a spinner that runs around the LED ring."""
    start_time = time.time()
    while (time.time() - start_time) < duration:
        for i in range(LED_COUNT):
            pixels.fill((0, 0, 0))  # Turn off all
            pixels[i] = parse_color(color)  # Bright green dot
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


def is_wifi_connected():
    try:
        # Try to get IP of wlan0 interface
        ip = subprocess.check_output("ip -4 addr show wlan0 | grep inet", shell=True).decode()
        return "inet" in ip
    except subprocess.CalledProcessError:
        return False

def start_access_point():
    hostname = socket.gethostname()
    ssid = hostname
    password = "pass1234"

    print(f"Starting AP with SSID: {ssid}, Password: {password}")

    # Set static IP
    subprocess.run(["sudo", "ifconfig", "wlan0", "192.168.4.1"])

    # Generate hostapd config
    hostapd_conf = f"""
interface=wlan0
ssid={ssid}
hw_mode=g
channel=7
auth_algs=1
wmm_enabled=0
wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
"""
    with open("/tmp/hostapd.conf", "w") as f:
        f.write(hostapd_conf)

    # Point hostapd to our config
    subprocess.run(["sudo", "sed", "-i", 's|#DAEMON_CONF=.*|DAEMON_CONF="/tmp/hostapd.conf"|', "/etc/default/hostapd"])

    # Stop conflicting services
    subprocess.run(["sudo", "systemctl", "stop", "wpa_supplicant"])
    subprocess.run(["sudo", "systemctl", "stop", "dhcpcd"])

    # Start access point
    subprocess.run(["sudo", "systemctl", "start", "hostapd"])

def start():
    if is_wifi_connected():
        print("Wi-Fi is connected. Nothing to do.")
        time.sleep(0.5)
        spinner_animation(color="000255000", duration=3.0)
    else:
        print("Wi-Fi NOT connected. Launching Access Point...")
        start_access_point()
        time.sleep(1.0)
        spinner_animation(color="000000255", duration=2.0)
        



# --- Run Boot Animation ---
spinner_animation(color="255255255")
start()

print('Waiting for NFC card...')
while True:
    uid = pn532.read_passive_target(timeout=0.5)
    if uid is not None:
        id =uid.hex()
        print(id)
        tap(id)