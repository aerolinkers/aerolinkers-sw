import requests
import time

SERVER = "http://192.168.0.138:7000"
PNR    = "PT1065"
MAC    = "08:3A:F2:A8:31:01"

# Step 1: Sync on boot
res = requests.post(f"{SERVER}/sync", json={"device_id": MAC, "pnr": PNR})
print("SYNC:", res.json())

# Step 2: Poll alerts every 60s (like real ESP32)
while True:
    res = requests.get(f"{SERVER}/api/notifications/DEV001")
    print("ALERTS:", res.json())
    time.sleep(60)


