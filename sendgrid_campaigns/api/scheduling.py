import json

def schedule_campaign(client, campaign_id, schedule_time):
    """
    Schedule a campaign for sending.
    
    Args:
        client: SendGrid client
        campaign_id: ID of the campaign to schedule
        schedule_time: Time in RFC3339/ISO8601 format
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        schedule_body = {
            "send_at": schedule_time
        }
        
        print("Scheduling campaign:", json.dumps(schedule_body, indent=2))
        response = client.client.marketing.singlesends._(campaign_id).schedule.put(
            request_body=schedule_body
        )
        
        if response and response.status_code in [200, 201, 202]:
            print(f"Successfully scheduled campaign for: {schedule_time}")
            return True
            
        print(f"Unexpected response when scheduling: {response.status_code if response else 'No response'}")
        return False
        
    except Exception as e:
        print(f"Error scheduling campaign: {str(e)}")
        if hasattr(e, 'body'):
            print(f"Schedule error response: {e.body.decode('utf-8')}")
        return False
