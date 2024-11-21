import json
from datetime import datetime
from .sender import get_sender_email

__all__ = [
    'get_campaign_list',
    'get_campaign_details',
    'check_existing_campaign',
    'get_default_suppression_group',
    'create_contacts_list'
]

def get_existing_lists(client, name_prefix):
    """
    Get existing contact lists that start with the given prefix.
    
    Args:
        client: SendGrid client
        name_prefix: Prefix to search for in list names
        
    Returns:
        list: List of matching contact lists
    """
    try:
        response = client.client.marketing.lists.get()
        if not response or not response.body:
            return []
            
        data = json.loads(response.body.decode('utf-8'))
        lists = data.get('result', [])
        
        return [lst for lst in lists if lst.get('name', '').startswith(name_prefix)]
            
    except Exception as e:
        print(f"Warning - Error checking existing lists: {str(e)}")
        if hasattr(e, 'body'):
            print(f"API Response: {e.body.decode('utf-8')}")
        return []

def get_existing_contacts(client, emails):
    """
    Get existing contacts from SendGrid.
    
    Args:
        client: SendGrid client
        emails: List of email addresses to check
        
    Returns:
        set: Set of existing email addresses
    """
    try:
        # Format emails for search
        formatted_emails = [f'"{email}"' for email in emails]
        search_body = {
            "query": f"(email in [{','.join(formatted_emails)}])"
        }
        
        response = client.client.marketing.contacts.search.post(request_body=search_body)
        if not response or not response.body:
            return set()
            
        data = json.loads(response.body.decode('utf-8'))
        if not isinstance(data, dict):
            return set()
            
        contacts = data.get('result', [])
        return {contact.get('email') for contact in contacts if contact.get('email')}
        
    except Exception as e:
        print(f"Warning - Error checking existing contacts: {str(e)}")
        if hasattr(e, 'body'):
            print(f"API Response: {e.body.decode('utf-8')}")
        return set()

def create_contacts_list(client, list_name, contacts):
    """
    Create or update a contacts list in SendGrid.
    
    Args:
        client: SendGrid client
        list_name: Name for the contacts list
        contacts: List of email addresses
        
    Returns:
        str: List ID if successful, None otherwise
    """
    try:
        # Check for existing lists with same name prefix
        base_name = list_name.split(' - ')[0]
        existing_lists = get_existing_lists(client, base_name)
        
        if existing_lists:
            print(f"Found {len(existing_lists)} existing lists with similar name")
            list_id = existing_lists[0].get('id')
            print(f"Using existing list: {existing_lists[0].get('name')}")
        else:
            # Create new list
            list_body = {
                "name": list_name
            }
            response = client.client.marketing.lists.post(request_body=list_body)
            if not response or not response.body:
                raise ValueError("Empty response when creating list")
                
            list_data = json.loads(response.body.decode('utf-8'))
            list_id = list_data.get('id')
            
            if not list_id:
                raise ValueError("No list ID in response")
                
            print(f"Created new list: {list_name}")

        # Handle contacts
        contacts_body = {
            "list_ids": [list_id],
            "contacts": [{"email": email} for email in contacts]
        }
        
        # Add/update all contacts in one go
        add_response = client.client.marketing.contacts.put(request_body=contacts_body)
        if not add_response or add_response.status_code not in [200, 201, 202]:
            raise ValueError("Failed to update contacts in list")
            
        print(f"Successfully added/updated {len(contacts)} contacts to the list")
        
        return list_id
        
    except Exception as e:
        print(f"Error managing contacts list: {str(e)}")
        if hasattr(e, 'body'):
            print(f"API Response: {e.body.decode('utf-8')}")
        return None

def get_suppression_groups(client):
    """
    Get list of available suppression groups.
    """
    try:
        response = client.client.asm.groups.get()
        if not response or not response.body:
            return []
            
        groups = json.loads(response.body.decode('utf-8'))
        if not isinstance(groups, list):
            return []
            
        return groups
        
    except Exception as e:
        print(f"Error getting suppression groups: {str(e)}")
        if hasattr(e, 'body'):
            print(f"API Response: {e.body.decode('utf-8')}")
        return []

def get_default_suppression_group(client):
    """
    Get the first available suppression group or create one if none exists.
    """
    groups = get_suppression_groups(client)
    
    if groups:
        return groups[0]['id']
        
    # Create a new suppression group if none exists
    try:
        group_body = {
            "name": "Default Unsubscribe Group",
            "description": "Default group for managing email unsubscriptions",
            "is_default": True
        }
        
        response = client.client.asm.groups.post(request_body=group_body)
        if not response or not response.body:
            raise ValueError("Empty response when creating suppression group")
            
        group_data = json.loads(response.body.decode('utf-8'))
        return group_data.get('id')
        
    except Exception as e:
        print(f"Error creating suppression group: {str(e)}")
        if hasattr(e, 'body'):
            print(f"API Response: {e.body.decode('utf-8')}")
        raise

def get_campaign_list(client):
    """
    Returns a list of all campaigns with their basic information.
    """
    try:
        response = client.client.marketing.singlesends.get()
        if not response or not response.body:
            return []
            
        data = json.loads(response.body.decode('utf-8'))
        if not isinstance(data, dict):
            return []
            
        campaign_list = data.get('result', [])
        if not campaign_list:
            return []
        
        # Get sender information
        sender_response = client.client.marketing.senders.get()
        senders = {}
        if sender_response and sender_response.body:
            sender_data = json.loads(sender_response.body.decode('utf-8'))
            if isinstance(sender_data, list):
                for sender in sender_data:
                    senders[sender.get('id')] = sender.get('from', {}).get('email')
        
        campaigns = []
        for campaign in campaign_list:
            campaign_stats = get_detailed_stats(client, campaign.get('id'))
            campaigns.append({
                'campaign_id': campaign.get('id'),
                'subject': campaign.get('name'),
                'scheduled_at': campaign.get('send_at'),
                'from': senders.get(campaign.get('sender_id'), 'Unknown'),
                'status': campaign.get('status'),
                'stats': campaign_stats
            })
        
        return campaigns
    
    except Exception as e:
        print(f"Error getting campaign list: {str(e)}")
        if hasattr(e, 'body'):
            print(f"API Response: {e.body.decode('utf-8')}")
        return []

def get_detailed_stats(client, campaign_id):
    """
    Get detailed stats for a campaign including delivery information.
    """
    try:
        # Get basic stats
        stats_response = client.client.marketing.stats.singlesends._(campaign_id).get()
        stats = {}
        if stats_response and stats_response.body:
            stats = json.loads(stats_response.body.decode('utf-8'))

        return stats
    except Exception as e:
        print(f"Warning - Error getting stats: {str(e)}")
        if hasattr(e, 'body'):
            print(f"API Response: {e.body.decode('utf-8')}")
        return {}

def get_campaign_details(client, campaign_id):
    """
    Returns detailed information about a specific campaign.
    """
    try:
        response = client.client.marketing.singlesends._(campaign_id).get()
        if not response or not response.body:
            return None
            
        campaign = json.loads(response.body.decode('utf-8'))
        
        # Get sender information
        sender_response = client.client.marketing.senders.get()
        sender_email = 'Unknown'
        if sender_response and sender_response.body:
            sender_data = json.loads(sender_response.body.decode('utf-8'))
            if isinstance(sender_data, list):
                for sender in sender_data:
                    if sender.get('id') == campaign.get('sender_id'):
                        sender_email = sender.get('from', {}).get('email')
                        break
        
        # Get detailed stats
        stats = get_detailed_stats(client, campaign_id)
            
        return {
            'campaign_id': campaign.get('id'),
            'subject': campaign.get('name'),
            'scheduled_at': campaign.get('send_at'),
            'from': sender_email,
            'html_content': campaign.get('email_config', {}).get('html_content')[:255] + "..." if campaign.get('email_config', {}).get('html_content') else None,
            'status': campaign.get('status'),
            'send_to': campaign.get('send_to'),
            'stats': stats,
            'last_checked': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        print(f"Error getting campaign details: {str(e)}")
        if hasattr(e, 'body'):
            print(f"API Response: {e.body.decode('utf-8')}")
        return None

def check_existing_campaign(client, subject):
    """
    Check if a campaign with the given subject already exists.
    """
    try:
        campaigns = get_campaign_list(client)
        for campaign in campaigns:
            if campaign.get('subject') == subject:
                return campaign
        return None
        
    except Exception as e:
        print(f"Error checking existing campaign: {str(e)}")
        if hasattr(e, 'body'):
            print(f"API Response: {e.body.decode('utf-8')}")
        return None
