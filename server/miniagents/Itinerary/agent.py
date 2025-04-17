import os
import json
import re
import logging
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Import other agents
from miniagents.Attractions.agent import attractions_search_agent, format_attractions_results
from miniagents.Flight.agent import flight_search_agent, format_flight_results
from miniagents.Hotels.agent import hotel_search_agent, format_hotel_results
from miniagents.Restaurants.agent import restaurant_search_agent, format_restaurant_results

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("itinerary_agent")

# ------------------ User Input Collection ------------------ #
def itinerary_agent(natural_language_input=None):
    print("🌴 Welcome to Vacation Itinerary Planner! 🌴")
    print("Let's gather some information to plan your perfect trip.\n")

    initial_details = {}

    if natural_language_input:
        destination_match = re.search(r"(?:to|in|at|for)\s+([A-Za-z\s,]+?)(?:for|from|on|with|\.|\?|$)", natural_language_input)
        if destination_match:
            initial_details["destination"] = destination_match.group(1).strip()

        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", natural_language_input)
        if date_match:
            initial_details["start_date"] = date_match.group(1)

        days_match = re.search(r"(\d+)\s+days", natural_language_input)
        if days_match:
            initial_details["num_days"] = int(days_match.group(1))

        travelers_match = re.search(r"(\d+)\s+(?:adults|people|travelers)", natural_language_input)
        if travelers_match:
            initial_details["adults"] = int(travelers_match.group(1))

        origin_match = re.search(r"from\s+([A-Za-z\s,]+)(?:to|for|on|\.|\?|$)", natural_language_input)
        if origin_match:
            initial_details["origin"] = origin_match.group(1).strip()

        budget_match = re.search(r"(economy|budget|affordable|mid-range|moderate|luxury|luxurious|high-end)", natural_language_input, re.IGNORECASE)
        if budget_match:
            budget_term = budget_match.group(1).lower()
            if budget_term in ["economy", "budget", "affordable"]:
                initial_details["budget_range"] = "economy"
            elif budget_term in ["mid-range", "moderate"]:
                initial_details["budget_range"] = "mid-range"
            elif budget_term in ["luxury", "luxurious", "high-end"]:
                initial_details["budget_range"] = "luxury"

    def get_input(key, question, cast=str):
        if key not in initial_details:
            while True:
                value = input(question)
                try:
                    return cast(value)
                except Exception:
                    print("❌ Invalid input. Please try again.")

    initial_details["destination"] = get_input("destination", "Where would you like to go? (city, country): ")
    initial_details["origin"] = get_input("origin", "What is your departure city for flights? ")
    initial_details["start_date"] = get_input("start_date", "What is your departure date? (YYYY-MM-DD): ", str)
    initial_details["num_days"] = get_input("num_days", "How many days will you be staying? ", int)
    initial_details["adults"] = get_input("adults", "How many adults are traveling? ", int)
    initial_details["budget_range"] = get_input("budget_range", "What is your budget range? (economy, mid-range, luxury): ", str)
    initial_details["interests"] = input("What are your interests? (e.g., museums, beaches, food, shopping): ")

    # Calculate end date
    start_date = datetime.strptime(initial_details["start_date"], "%Y-%m-%d")
    end_date = start_date + timedelta(days=initial_details["num_days"])
    initial_details["end_date"] = end_date.strftime("%Y-%m-%d")

    print("\n✅ Collected all trip details!\n")
    return initial_details

# ------------------ Plan Itinerary ------------------ #
def plan_itinerary(vacation_details: Dict[str, Any]) -> Dict[str, Any]:
    try:
        logger.info("Planning itinerary with details: %s", vacation_details)
        itinerary_results = {"success": True, "itinerary": {}}

        flight_query = f"from={vacation_details['origin']}&to={vacation_details['destination']}&departureDate={vacation_details['start_date']}&returnDate={vacation_details['end_date']}&adults={vacation_details['adults']}"
        flight_results = flight_search_agent(input_str=flight_query)
        itinerary_results["itinerary"]["flights"] = flight_results

        hotel_query = f"city={vacation_details['destination']}&checkInDate={vacation_details['start_date']}&checkOutDate={vacation_details['end_date']}&adults={vacation_details['adults']}"
        hotel_results = hotel_search_agent(input_str=hotel_query)
        itinerary_results["itinerary"]["hotels"] = hotel_results

        attractions_query = f"location={vacation_details['destination']}"
        attractions_results = attractions_search_agent(input_str=attractions_query)
        itinerary_results["itinerary"]["attractions"] = attractions_results

        restaurant_query = f"location={vacation_details['destination']}"
        restaurant_results = restaurant_search_agent(input_str=restaurant_query)
        itinerary_results["itinerary"]["restaurants"] = restaurant_results

        return itinerary_results

    except Exception as e:
        logger.error("Itinerary Planning Exception: %s", e)
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}

# ------------------ Format Itinerary ------------------ #
def format_daily_itinerary(vacation_details: Dict[str, Any], itinerary_results: Dict[str, Any]) -> str:
    if not itinerary_results.get("success", False):
        return f"❌ Failed to create itinerary: {itinerary_results.get('error', 'Unknown error')}"

    itinerary = itinerary_results.get("itinerary", {})
    msg = f"# 🌴 {vacation_details['num_days']}-Day Itinerary for {vacation_details['destination']} 🌴\n\n"
    msg += "## ✈️ Travel Details\n\n"

    if "flights" in itinerary:
        msg += format_flight_results(itinerary["flights"]) + "\n\n"

    msg += "## 🏨 Accommodation\n\n"
    if "hotels" in itinerary:
        msg += format_hotel_results(itinerary["hotels"]) + "\n\n"

    msg += "## 📅 Day-by-Day Itinerary\n\n"

    attractions = itinerary.get("attractions", {}).get("attractions", {}).get("attractions_list", {}).get("attractions", [])
    restaurants = itinerary.get("restaurants", {}).get("restaurants", {}).get("restaurants", [])

    start_date = datetime.strptime(vacation_details["start_date"], "%Y-%m-%d")
    for day in range(vacation_details["num_days"]):
        date = start_date + timedelta(days=day)
        msg += f"### Day {day+1}: {date.strftime('%A, %B %d, %Y')}\n\n"

        if day < len(attractions):
            a = attractions[day]
            msg += f"**Morning:** Visit {a.get('name', 'an attraction')}\n"
        else:
            msg += "**Morning:** Free time to explore.\n"

        if day < len(restaurants):
            r = restaurants[day]
            msg += f"**Lunch:** Dine at {r.get('name', 'a local restaurant')}\n"
        else:
            msg += "**Lunch:** Explore local cuisine.\n"

        if day+1 < len(attractions):
            a = attractions[(day+1) % len(attractions)]
            msg += f"**Afternoon:** Explore {a.get('name', 'another attraction')}\n"
        else:
            msg += "**Afternoon:** Relax or shop.\n"

        if day+1 < len(restaurants):
            r = restaurants[(day+1) % len(restaurants)]
            msg += f"**Dinner:** Enjoy dinner at {r.get('name', 'a local restaurant')}\n"
        else:
            msg += "**Dinner:** Choose a local spot.\n"

        msg += "\n"

    msg += "## 📝 Additional Information\n"
    msg += f"- Budget: {vacation_details['budget_range']}\n"
    msg += f"- Interests: {vacation_details['interests']}\n"

    return msg

# ------------------ CLI ------------------ #
def main():
    print("=" * 50)
    print("🌍 Welcome to the Travel Itinerary Planning Agent! 🌍")
    print("=" * 50)
    print("\nTell me about your trip, or answer a few questions.\n")
    initial_input = input("How can I help you plan your vacation? ")

    vacation_details = itinerary_agent(initial_input)
    if vacation_details:
        print("\n🔎 Planning your trip... Please wait!\n")
        itinerary_results = plan_itinerary(vacation_details)
        itinerary_output = format_daily_itinerary(vacation_details, itinerary_results)
        
        print("\n" + "=" * 50 + "\n")
        print(itinerary_output)
        print("\n" + "=" * 50 + "\n")

        save = input("Would you like to save this itinerary to a file? (yes/no): ")
        if save.lower() == "yes":
            filename = f"itinerary_{vacation_details['destination'].replace(' ', '_')}_{vacation_details['start_date']}.md"
            with open(filename, "w") as f:
                f.write(itinerary_output)
            print(f"✅ Itinerary saved to {filename}")

if __name__ == "__main__":
    main()
