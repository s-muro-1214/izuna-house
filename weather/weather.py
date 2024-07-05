
import requests_cache
import os
import time
from retry_requests import retry
from prometheus_client import start_http_server, Counter, Gauge, Info
from dotenv import load_dotenv


# for prometheus
openweather_api_calls_total = Counter("openweather_api_calls_total", "Number of API calls to openweathermap.org", ["endpoint", "location", "response_status"])
openweather_sunrise = Gauge("openweather_sunrise", "Sunrise time, Unix, UTC", ["location"])
openweather_sunset = Gauge("openweather_sunset", "Sunset time, Unix, UTC", ["location"])
openweather_temperature = Gauge("openweather_temperature", "Current temperature in degrees", ["location"])
openweather_feels_like = Gauge("openweather_feels_like", "Current feels_like temperature in degrees", ["location"])
openweather_pressure = Gauge("openweather_pressure", "Current atmospheric pressure on the sea level, hPa", ["location"])
openweather_humidity = Gauge("openweather_humidity", "Current humidity, %", ["location"])
openweather_dew_point =Gauge("openweather_dew_point", "Atmospheric temperature below which water droplets begin to condense and dew can form", ["location"])
openweather_clouds = Gauge("openweather_clouds", "Current cloudiness, %", ["location"])
openweather_uvi = Gauge("openweather_uvi", "Current UV index", ["location"])
openweather_visibility = Gauge("openweather_visibility", "Average visibility, metres. The maximum value of the visibility is 10 km", ["location"])
openweather_wind_speed = Gauge("openweather_wind_speed", "Current Wind Speed in mph or meters/sec if imperial", ["location"])
openweather_wind_gust = Gauge("openweather_wind_gust", "Current Wind Gusts in mph or meters/sec if imperial", ["location"])
openweather_wind_deg  = Gauge("openweather_wind_deg", "Wind direction, degrees (meteorological)", ["location"])
openweather_rain1h = Gauge("openweather_rain1h", "Rain volume for last hour, in millimeters", ["location"])
openweather_snow1h = Gauge("openweather_snow1h", "Snow volume for last hour, in millimeters", ["location"])
openweather_currentconditions = Gauge("openweather_currentconditions", "Current weather conditions", ["location", "description", "icon"])

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)

load_dotenv()


def get_geocoding(zipcode: str):
    base_url = "http://api.openweathermap.org/geo/1.0/zip"
    params = {
        "zip": zipcode,
        "appid": os.getenv("APPID")
    }

    print(f"Looking up: {zipcode}")
    response = retry_session.get(base_url, params=params)

    if response.status_code == 200:
        data = response.json()
        
        lat = data["lat"]
        lon = data["lon"]
        location = f"{data['name']}, {data['country']}"

        print(f"Latitude: {lat} Longitude: {lon} for {location}")
        return location, lat, lon

    print(f"Error: {response.status_code}")


def update_current_weather(location: str, lat: float, lon: float):
    base_url = "https://api.openweathermap.org/data/3.0/onecall"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": os.getenv("APPID"),
        "exclude": "minutely,hourly,daily",
        "units": "metric",
        "lang": "ja"
    }

    response = retry_session.get(base_url, params=params)
    response_status = f"{response.status_code} {response.reason}"

    openweather_api_calls_total.labels(base_url, location, response_status).inc()

    if response.status_code == 200:
        data = response.json()["current"]

        openweather_sunrise.labels(location).set(data["sunrise"] * 1000)
        openweather_sunset.labels(location).set(data["sunset"] * 1000)
        openweather_temperature.labels(location).set(data["temp"])
        openweather_feels_like.labels(location).set(data["feels_like"])
        openweather_pressure.labels(location).set(data["pressure"])
        openweather_humidity.labels(location).set(data["humidity"])
        openweather_dew_point.labels(location).set(data["dew_point"])
        openweather_clouds.labels(location).set(data["clouds"])
        openweather_uvi.labels(location).set(data["uvi"])
        openweather_visibility.labels(location).set(data["visibility"])
        openweather_wind_speed.labels(location).set(data["wind_speed"])
        openweather_wind_gust.labels(location).set(data["wind_gust"])
        openweather_wind_deg.labels(location).set(data["wind_deg"])
        openweather_rain1h.labels(location).set(data.get("rain", {}).get("1h", 0.0))
        openweather_snow1h.labels(location).set(data.get("snow", {}).get("1h", 0.0))
        openweather_currentconditions.labels(location, data["weather"][0]["description"], data["weather"][0]["icon"])


if __name__ == "__main__":
    start_http_server(9494)

    geo = get_geocoding(f"{os.getenv('ZIPCODE')},{os.getenv('COUNTRY')}")

    print("Beginning to serve on port :9494")
    while True:
        update_current_weather(geo[0], geo[1], geo[2])
        time.sleep(180)
