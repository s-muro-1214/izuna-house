import base64
import hmac
import hashlib
import requests_cache
import os
import time
import uuid
from retry_requests import retry
from prometheus_client import start_http_server, Counter, Gauge, Info
from dotenv import load_dotenv

# for prometheus
switchbot_api_calls_total = Counter("switchbot_api_calls_total", "Number of API calls to switchbot API", ["endpoint", "DeviceID", "response_status"])
switchbot_curtain_battery = Gauge("switchbot_curtain_battery", "Battery Percentage", ["DeviceID"])

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 300)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)

load_dotenv()

# for switchbot API v1.1
token = os.getenv("SWITCHBOT_TOKEN")
secret = os.getenv("SWITCHBOT_SECRET")
nonce = str(uuid.uuid4())
t = int(round(time.time() * 1000))
string_to_sign = bytes(f"{token}{t}{nonce}", "utf-8")
secret = bytes(secret, "utf-8")
sign = base64.b64encode(
    hmac.new(secret, msg=string_to_sign, digestmod=hashlib.sha256).digest()
)

apiHeader = {}
apiHeader["Authorization"] = token
apiHeader["Content-Type"] = "application/json"
apiHeader["charset"] = "utf8"
apiHeader["t"] = str(t)
apiHeader["sign"] = str(sign, "utf-8")
apiHeader["nonce"] = nonce


def update_current_battery(device_id: str):
    base_url = "https://api.switch-bot.com/v1.1/devices"
    url = f"{base_url}/{device_id}/status"

    response = retry_session.get(url, headers=apiHeader)
    response_status = f"{response.status_code} {response.reason}"
    
    switchbot_api_calls_total.labels(base_url, device_id, response_status).inc()

    if response.status_code == 200:
        data = response.json()["body"]

        switchbot_curtain_battery.labels(device_id).set(data["battery"])


if __name__ == "__main__":
    device_ids = os.getenv("SWITCHBOT_DEVICES")
    device_list = device_ids.split(",")

    start_http_server(9495)

    print("Beginning to serve on port :9495")
    while True:
        for device_id in device_list:
            update_current_battery(device_id)
        time.sleep(180)
