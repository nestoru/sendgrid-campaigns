import json
from datetime import datetime
from .utils.file_utils import parse_receivers_file, read_html_content
from .utils.date_utils import parse_schedule_time
from .api.sender import get_sender_id
from .api.campaign import (get_campaign_list, get_campaign_details, 
                         check_existing_campaign, get_default_suppression_group,
                         create_contacts_list)
from .api.scheduling import schedule_campaign

def create_or_update_campaign(client, args):
    """
    Creates a new campaign or updates an existing one using SingleSends API.
    """
    if args.campaign_id:
        # Check campaign status before update
        current_details = get_campaign_details(client, args.campaign_id)
        if current_details and current_details.get('status') != 'draft':
            raise ValueError(
                f"Campaign cannot be updated because its status is '{current_details.get('status')}'.\n"
                "Only campaigns in 'draft' status can be updated."
            )

    # If no campaign_id provided, check if campaign exists
    if not args.campaign_id:
        existing_campaign = check_existing_campaign(client, args.subject)
        if existing_campaign:
            raise ValueError(
                f"A campaign with the subject '{args.subject}' already exists.\n"
                f"Existing campaign details:\n"
                f"- Campaign ID: {existing_campaign['campaign_id']}\n"
                f"- Subject: {existing_campaign['subject']}\n"
                f"- Scheduled At: {existing_campaign['scheduled_at']}\n"
                f"- From: {existing_campaign['from']}\n"
                f"- Status: {existing_campaign.get('status', 'Unknown')}\n"
                f"To update this campaign, please provide its campaign_id."
            )

    # Parse files and get required data
    receivers = parse_receivers_file(args.receivers_file_path)
    html_body = read_html_content(args.html_body_file_path)
    
    # Print truncated HTML preview
    print(f"\nHTML content preview (first 255 characters):")
    print(f"{html_body[:255]}...")
    print()
    
    sender_id = get_sender_id(client, args.sender)
    schedule_time = parse_schedule_time(args.scheduled_at)
    
    # Get or create suppression group
    suppression_group_id = get_default_suppression_group(client)

    # Create a contact list for these receivers
    list_name = f"List for {args.subject} - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    list_id = create_contacts_list(client, list_name, receivers)
    
    if not list_id:
        raise ValueError("Failed to create contacts list")

    # Create the campaign request body
    campaign_body = {
        "name": args.subject,
        "email_config": {
            "subject": args.subject,
            "html_content": html_body,  # SendGrid will handle the CID references
            "sender_id": sender_id,
            "suppression_group_id": suppression_group_id,
            "tracking_settings": {
                "click_tracking": {
                    "enable": False
                },
                "open_tracking": {
                    "enable": False
                },
                "subscription_tracking": {
                    "enable": False
                }
            }
        },
        "send_to": {
            "list_ids": [list_id]
        }
    }

    try:
        # When printing the body, exclude html_content for clarity
        print_body = campaign_body.copy()
        print_body['email_config'] = {k: v for k, v in print_body['email_config'].items() if k != 'html_content'}
        print("Creating campaign with body:", json.dumps(print_body, indent=2))
        
        if args.campaign_id:
            # Update existing campaign
            response = client.client.marketing.singlesends._(args.campaign_id).patch(request_body=campaign_body)
            campaign_id = args.campaign_id
            print(f"Updated existing campaign with ID: {campaign_id}")
        else:
            # Create new campaign
            response = client.client.marketing.singlesends.post(request_body=campaign_body)
            if not response or not response.body:
                raise ValueError("Empty response from SendGrid API when creating campaign")
                
            response_data = json.loads(response.body.decode('utf-8'))
            campaign_id = response_data.get("id")
            if not campaign_id:
                raise ValueError(f"No campaign ID in response: {response_data}")
            print(f"Created new campaign with ID: {campaign_id}")

        # Schedule the campaign
        if not schedule_campaign(client, campaign_id, schedule_time):
            print("Warning: Campaign created but scheduling failed")

        # Get and show final campaign details
        final_details = get_campaign_details(client, campaign_id)
        print("\nFinal Campaign Details:")
        print(json.dumps(final_details, indent=2))

        return campaign_id

    except Exception as e:
        print(f"Error in API request: {str(e)}")
        if hasattr(e, 'body'):
            error_body = e.body.decode('utf-8')
            print(f"API Response: {error_body}")
            try:
                error_json = json.loads(error_body)
                if 'errors' in error_json:
                    for error in error_json['errors']:
                        print(f"Field: {error.get('field', 'N/A')}")
                        print(f"Message: {error.get('message', 'N/A')}")
            except json.JSONDecodeError:
                pass
        raise

def process_campaign_request(client, args):
    """
    Main function to process campaign requests based on provided arguments.
    """
    # Build a list of provided arguments (excluding json_config_file_path and command)
    provided_args = [
        arg for arg in ['campaign_id', 'subject', 'sender',
                       'html_body_file_path', 'scheduled_at', 'receivers_file_path']
        if hasattr(args, arg) and getattr(args, arg) is not None
    ]
    
    # Case 1: Only json_config_file_path provided - return list of campaigns
    if not provided_args:
        campaigns = get_campaign_list(client)
        if not campaigns:
            return "No campaigns found"
        return campaigns
    
    # Case 2: Only campaign_id provided - return campaign details
    if provided_args == ['campaign_id']:
        details = get_campaign_details(client, args.campaign_id)
        if not details:
            return "No campaign found"
        return details
    
    # Check for all required fields for creation/update
    required_fields = ['subject', 'sender', 'receivers_file_path',
                      'html_body_file_path', 'scheduled_at']
    
    has_all_required = all(field in provided_args for field in required_fields)
    
    # Case 3 & 4: All required fields present (with or without campaign_id)
    if has_all_required:
        return create_or_update_campaign(client, args)
        
    # Invalid combination of arguments
    raise ValueError(
        "You can pass:\n"
        "1. No arguments to get a list of campaigns\n"
        "2. Just a campaign_id to get the details for that campaign\n"
        "3. All arguments except campaign_id to create a new campaign\n"
        "4. All arguments including campaign_id to replace an existing campaign"
    )
