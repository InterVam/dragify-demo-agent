import json
import logging
import re
from langchain_core.tools import tool
from app.utils.logger import log_json
from app.config.llm import get_llm

logger = logging.getLogger(__name__)

@tool(return_direct=False)
def extract_lead_info(message: str) -> dict:
    """
    Extract structured lead info from a sales rep's Slack message.
    Output is a dictionary with:
    - first_name
    - last_name
    - phone
    - location
    - property_type
    - bedrooms
    - budget (as an integer, e.g., 3500000)
    """
    try:
        logger.info("Extracting lead info from message using LLM")
        log_json("Incoming Message", {"message": message})

        llm = get_llm()
        prompt = f"""Extract lead information from this sales message and return ONLY valid JSON.

Message: "{message}"

Extract these exact fields (use empty string "" if not found, except budget which should default to 0 if missing):
- first_name
- last_name
- phone
- location
- property_type
- bedrooms
- budget (in Egyptian Pounds as integer; convert '5M', '3.5M', etc. to 5000000, 3500000)

Return ONLY this JSON format:
{{"first_name": "", "last_name": "", "phone": "", "location": "", "property_type": "", "bedrooms": "", "budget": 0}}

Examples:
Input: "Spoke with Sarah Johnson about 3BR villa in New Cairo, budget 8M, her number 01234567890"
Output: {{"first_name": "Sarah", "last_name": "Johnson", "phone": "01234567890", "location": "New Cairo", "property_type": "villa", "bedrooms": "3", "budget": 8000000}}

Input: "She needs a 1 bedroom studio in Maadi. Budget 1M. Contact: 0100000000"
Output: {{"first_name": "", "last_name": "", "phone": "0100000000", "location": "Maadi", "property_type": "studio", "bedrooms": "1", "budget": 1000000}}

Now extract from the message above:"""

        response = llm.invoke(prompt)
        if not response or not hasattr(response, "content"):
            raise ValueError("Invalid LLM response")

        text = response.content.strip()
        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()

        start_idx = text.find("{")
        end_idx = text.rfind("}")
        lead_info = {}
        if start_idx != -1 and end_idx != -1:
            try:
                lead_info = json.loads(text[start_idx:end_idx+1])
            except json.JSONDecodeError:
                json_candidates = re.findall(r"\{.*?\}", text, re.DOTALL)
                for candidate in json_candidates:
                    try:
                        lead_info = json.loads(candidate)
                        break
                    except json.JSONDecodeError:
                        continue

        required_keys = [
            "first_name", "last_name", "phone",
            "location", "property_type", "bedrooms", "budget"
        ]
        for key in required_keys:
            if key != "budget":
                lead_info[key] = str(lead_info.get(key, "") or "")
            else:
                budget_val = lead_info.get("budget", 0)
                if isinstance(budget_val, str):
                    budget_val = budget_val.upper().replace(" ", "")
                    if budget_val.endswith("M"):
                        try:
                            budget_val = float(budget_val[:-1]) * 1_000_000
                        except ValueError:
                            budget_val = 0
                    elif re.match(r"^\d+(\.\d+)?$", budget_val):
                        budget_val = float(budget_val)
                    else:
                        budget_val = 0
                try:
                    lead_info["budget"] = int(budget_val)
                except:
                    lead_info["budget"] = 0

        word_to_num = {
            "one": "1", "two": "2", "three": "3", "four": "4",
            "five": "5", "six": "6", "seven": "7", "eight": "8"
        }
        b = lead_info.get("bedrooms", "").lower()
        if b in word_to_num:
            lead_info["bedrooms"] = word_to_num[b]

        log_json("Lead Info", lead_info)
        return lead_info

    except Exception as e:
        logger.error(f"extract_lead_info failed: {str(e)}", exc_info=True)
        return {
            "first_name": "", "last_name": "", "phone": "",
            "location": "", "property_type": "", "bedrooms": "", "budget": 0
        }

