import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent")

def log_json(label, data):
    logger.info(f"{label}: {json.dumps(data, indent=2)}")
