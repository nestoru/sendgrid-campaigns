import json

def get_sender_id(client, sender_email):
    """
    Fetches the sender ID for a given sender email using the SendGrid API.
    """
    if not sender_email:
        return None
        
    try:
        response = client.client.marketing.senders.get()
        if not response or not response.body:
            raise ValueError("Empty response from SendGrid API")
            
        senders = json.loads(response.body.decode('utf-8'))
        if not isinstance(senders, list):
            senders = []
        
        for sender in senders:
            if (sender.get('from', {}).get('email') == sender_email):
                return sender['id']
        
        raise ValueError(f"No verified sender found for email: {sender_email}")
    
    except Exception as e:
        print(f"Error getting sender ID: {str(e)}")
        if hasattr(e, 'body'):
            print(f"API Response: {e.body.decode('utf-8')}")
        raise

def get_sender_email(client, sender_id):
    """
    Get sender email from sender ID.
    """
    try:
        response = client.client.marketing.senders.get()
        if not response or not response.body:
            return 'Unknown'
            
        senders = json.loads(response.body.decode('utf-8'))
        if not isinstance(senders, list):
            return 'Unknown'
            
        for sender in senders:
            if sender.get('id') == sender_id:
                return sender.get('from', {}).get('email', 'Unknown')
                
        return 'Unknown'
        
    except Exception:
        return 'Unknown'
