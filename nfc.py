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


def is_connected():
    """Returns True if connected to Wi-Fi, otherwise False."""
    try:
        result = subprocess.run(
            ["iwgetid"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        return result.stdout != b''
    except:
        return False

def start_ap():
    """Starts Access Point mode."""
    print("Starting Access Point...")
    subprocess.run(["sudo", "ifconfig", "wlan0", "down"])
    subprocess.run(["sudo", "ifconfig", "wlan0", "192.168.4.1", "netmask", "255.255.255.0", "up"])
    subprocess.run(["sudo", "systemctl", "start", "dnsmasq"])
    subprocess.run(["sudo", "systemctl", "start", "hostapd"])

def stop_ap():
    """Stops Access Point mode and resets Wi-Fi."""
    print("Stopping Access Point...")
    subprocess.run(["sudo", "systemctl", "stop", "hostapd"])
    subprocess.run(["sudo", "systemctl", "stop", "dnsmasq"])
    subprocess.run(["sudo", "ifconfig", "wlan0", "down"])
    subprocess.run(["sudo", "ifconfig", "wlan0", "up"])

def is_wifi_connected():
    try:
        # Try to get IP of wlan0 interface
        ip = subprocess.check_output("ip -4 addr show wlan0 | grep inet", shell=True).decode()
        return "inet" in ip
    except subprocess.CalledProcessError:
        return False


def start_access_point(ssid="TapAP", password="pass1234"):
    print(f"Starting AP with SSID: {ssid}, Password: {password}")

    # 1. Write hostapd config
    hostapd_conf = f"""
interface=wlan0
driver=nl80211
ssid={ssid}
hw_mode=g
channel=6
auth_algs=1
wmm_enabled=1
wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
"""
    with open("/tmp/hostapd.conf", "w") as f:
        f.write(hostapd_conf)

    # 2. Stop interfering services
    subprocess.run("sudo systemctl stop wpa_supplicant.service", shell=True)
    subprocess.run("sudo killall wpa_supplicant", shell=True)

    # 3. Set static IP
    subprocess.run("sudo ifconfig wlan0 192.168.4.1 netmask 255.255.255.0 up", shell=True)

    # 4. Start dnsmasq for DHCP
    dnsmasq_conf = """
interface=wlan0
dhcp-range=192.168.4.10,192.168.4.100,12h
"""
    with open("/tmp/dnsmasq.conf", "w") as f:
        f.write(dnsmasq_conf)

    subprocess.run("sudo dnsmasq -C /tmp/dnsmasq.conf", shell=True)

    # 5. Start hostapd
    subprocess.run("sudo hostapd -B /tmp/hostapd.conf", shell=True)

    print("Access Point should now be active on 192.168.4.1")
    spinner_animation(color="122122122", duration=3.0)


def start():
    if is_connected():
        print("Connected to Wi-Fi, continuing in client mode.")
        spinner_animation(color="000255000", duration=2.0)
    else:
        spinner_animation(color="255000000")
        print("Not connected to Wi-Fi. Switching to AP mode.")
        start_ap()
        spinner_animation(color="000000255", duration=2.0, wait=0.08)



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