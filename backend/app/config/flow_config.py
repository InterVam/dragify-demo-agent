# Example static flow config; replace with DB in production
user_flows = {
    "team_default": {
        "data_source": "postgresql",
        "crm": "zoho",
        "notification_channel": "outlook"
    },
     "T090NR297QD": {  
        "data_source": "postgresql",
        "crm": "zoho",
        "notification_channel": "gmail"
    },
    "T01ABCDE123": {  
        "data_source": "sheets",
        "crm": "zoho",
        "notification_channel": "outlook"
    }
}

def get_user_flow(team_id: str) -> dict:
    return user_flows.get(team_id, user_flows["team_default"])
