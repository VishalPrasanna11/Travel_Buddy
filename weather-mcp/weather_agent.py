from langchain_openai import OpenAI
from langchain_core.prompts import PromptTemplate
import os


def create_weather_agent(openai_api_key):
    template = """You are a helpful weather reporter. Given the following weather data, generate a concise and informative weather report in natural language:

    Location: {location}
    Temperature: {temperature}
    Weather Condition: {weather_condition}
    Humidity: {humidity}
    Wind Speed: {wind_speed}
    Wind Direction: {wind_direction}

    Weather Report:"""

    prompt = PromptTemplate(
        input_variables=["location", "temperature", "weather_condition", "humidity", "wind_speed", "wind_direction"],
        template=template,
    )

    llm = OpenAI(temperature=0.7, openai_api_key=openai_api_key)
    chain = prompt | llm

    return chain


if __name__ == "__main__":
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    weather_agent = create_weather_agent(openai_api_key)

    weather_data = {
        "location": "London",
        "temperature": "15°C",
        "weather_condition": "Cloudy",
        "humidity": "80%",
        "wind_speed": "10 m/s",
        "wind_direction": "South",
    }

    report = weather_agent.invoke(weather_data)
    print(report)
