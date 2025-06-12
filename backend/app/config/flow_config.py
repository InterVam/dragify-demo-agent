# Example static flow config; replace with DB in production
user_flows = {
    "team_default": {
        "data_source": "postgresql",
        "crm": "odoo",
        "notification_channel": "gmail"
    },
    "T01ABCDE123": {  # real Slack team_id example
        "data_source": "sheets",
        "crm": "odoo",
        "notification_channel": "outlook"
    }
}

def get_user_flow(team_id: str) -> dict:
    return user_flows.get(team_id, user_flows["team_default"])
