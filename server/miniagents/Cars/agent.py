"""Car rental mini-agent: structured input → car_search tool, same contract as the other mini-agents."""
import logging
import re
import traceback
from typing import Any, Dict

from tools.car_search import car_search

logger = logging.getLogger("car_agent")


def car_search_agent(*, input_str: str) -> Dict[str, Any]:
    try:
        if not re.search(r"location=.*&pickup_date=.*&dropoff_date=", input_str):
            return {"error": "Use location=…&pickup_date=YYYY-MM-DD&dropoff_date=YYYY-MM-DD", "status": "error"}
        result = car_search.invoke(input_str)
        return {"formatted_text": result, "cars": result.get("cars", []), "api_data": result,
                "status": "error" if "error" in result else "success"}
    except Exception as e:
        logger.error(f"Car agent error: {e}\n{traceback.format_exc()}")
        return {"error": f"Internal error: {e}", "status": "error"}
