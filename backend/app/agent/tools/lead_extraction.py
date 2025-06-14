import json
import logging
import re
from langchain_core.tools import tool
from app.utils.logger import log_json
from app.config.llm import get_llm

logger = logging.getLogger(__name__)

@tool
def extract_lead_info(message: str, team_id: str) -> dict:
    """Extract lead info from message. Returns dict with lead details."""
    # Output keys
    keys = [
        'first_name', 'last_name', 'phone',
        'location', 'property_type', 'bedrooms', 'budget'
    ]
    try:
        logger.info("extract_lead_info: invoking LLM")
        log_json("Incoming Message", {"message": message})

        llm = get_llm()
        prompt = (
            "Extract JSON with exactly these keys: first_name, last_name, phone, "
            "location, property_type, bedrooms, budget. Return only JSON.\n\n"
            "For budget: Convert any format (5.5M, 2.3 million, 500K, etc.) to the raw number.\n"
            "Examples: '5.5M' -> '5500000', '2.3 million' -> '2300000', '500K' -> '500000'\n\n"
            f"Message: \"{message}\""
        )

        # Call synchronously
        response = llm.invoke(prompt)
        text = getattr(response, 'content', '') or ''
        text = text.strip()

        # Remove code fences
        text = re.sub(r"^```.*|```$", "", text, flags=re.M)

        # Extract JSON substring
        start = text.find('{')
        end = text.rfind('}')
        data = {}
        if start != -1 and end != -1:
            raw = text[start:end+1]
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                for cand in re.findall(r"\{.*?\}", text, flags=re.S):
                    try:
                        data = json.loads(cand)
                        break
                    except json.JSONDecodeError:
                        continue

        # Normalize and ensure keys
        for k in keys:
            val = data.get(k, "")
            if k == 'budget':
                s = str(val).upper().strip()
                
                # Enhanced budget parsing to handle various formats
                # Remove common currency symbols and clean up
                s = re.sub(r'[,$£€]', '', s)
                s = s.replace(' ', '')
                
                # Handle millions: 5.5M, 2.3 million, 1.5 M, etc.
                if 'M' in s or 'MILLION' in s:
                    # Extract the number part before M/MILLION
                    number_match = re.search(r'(\d+\.?\d*)', s)
                    if number_match:
                        try:
                            val = int(float(number_match.group(1)) * 1_000_000)
                        except:
                            val = 0
                    else:
                        val = 0
                        
                # Handle thousands: 500K, 750 thousand, etc.
                elif 'K' in s or 'THOUSAND' in s:
                    number_match = re.search(r'(\d+\.?\d*)', s)
                    if number_match:
                        try:
                            val = int(float(number_match.group(1)) * 1_000)
                        except:
                            val = 0
                    else:
                        val = 0
                        
                # Handle regular numbers: 3500000, 2500000, etc.
                else:
                    try:
                        # Extract only digits and decimal points
                        clean_number = re.sub(r'[^0-9\.]', '', s)
                        if clean_number:
                            val = int(float(clean_number))
                        else:
                            val = 0
                    except:
                        val = 0
                        
                data[k] = val
            else:
                data[k] = str(val or "")

        # Map bedroom words to numbers
        mapping = {"one":"1","two":"2","three":"3","four":"4"}
        b = data.get('bedrooms', '').lower()
        data['bedrooms'] = mapping.get(b, data.get('bedrooms', '').strip())

        # Inject team_id
        data['team_id'] = team_id
        log_json("Lead Info", data)
        return data

    except Exception as e:
        logger.error(f"extract_lead_info failed: {e}", exc_info=True)
        # Fallback
        fallback = {k: (0 if k == 'budget' else "") for k in keys}
        fallback['team_id'] = team_id
        return fallback
