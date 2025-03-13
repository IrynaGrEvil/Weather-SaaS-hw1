import os
import datetime as dt
import json
import requests
import openai
from flask import Flask, jsonify, request
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

app = Flask(__name__)

def get_weather(location: str, date: str):
    base_url = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
    url = f"{base_url}/{location}/{date}?key={WEATHER_API_KEY}&unitGroup=metric"

    response = requests.get(url)

    if response.status_code != 200:
        return {"error": f"Weather API error: {response.status_code} {response.text}"}

    data = response.json()

    if "days" not in data or not data["days"]:
        return {"error": "No weather data available for the given date"}

    weather_data = data["days"][0]

    return {
        "temp_c": weather_data.get("temp", None),
        "wind_kph": weather_data.get("windspeed", None),
        "pressure_mb": weather_data.get("pressure", None),
        "humidity": weather_data.get("humidity", None),
    }

def send_to_openai(weather_data):

    messages = [
        {"role": "system",
         "content": "You are a friendly and knowledgeable weather assistant. Your goal is to analyze weather data, "
                    "identify potential risks, and provide safety advice in a clear and engaging way."},
        {"role": "user",
         "content": f"Please analyze the following weather data:```\n{json.dumps(weather_data, indent=2)}\n```"
                    f"1. Summarize the key weather conditions briefly. Start your response with Hi!.\n"
                    f"2. Identify any potential risks, such as storms, blizzards, extreme heat, or high winds. "
                    f"If any risks are detected, issue a friendly but clear warning.\n"
                    f"3. Provide essential safety tips based on the current weather conditions (e.g., storm safety "
                    f"precautions, hydration reminders, cold weather protection, etc.).\n"
                    f"4. Suggest appropriate clothing choices for this weather in a warm and helpful tone.\n\n"
                    f"Keep your response concise yet informative (around 8-10 sentences). "
                    f"Write your answer as one paragraph."
         }
	]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error with OpenAI API: {str(e)}"

class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        return rv

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.route("/")
def home_page():
    return "<p><h2>Weather API Service with AI Analysis</h2></p>"

@app.route("/weather/api/v1/get", methods=["POST"])
def weather_endpoint():
    start_dt = dt.datetime.utcnow()
    json_data = request.get_json()

    if json_data.get("token") is None:
        raise InvalidUsage("Token is required", status_code=400)

    token = json_data.get("token")
    if token != API_TOKEN:
        raise InvalidUsage("Wrong API token", status_code=403)

    requester_name = json_data.get("requester_name")
    location = json_data.get("location")
    date = json_data.get("date")

    if not requester_name or not location or not date:
        raise InvalidUsage("Missing required fields: requester_name, location, or date", status_code=400)

    weather = get_weather(location, date)
    ai_analysis = send_to_openai(weather)

    end_dt = dt.datetime.utcnow()

    result = {
        "requester_name": requester_name,
        "timestamp": end_dt.isoformat() + "Z",
        "location": location,
        "date": date,
        "weather": weather,
        "ai_analysis": ai_analysis
    }

    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

