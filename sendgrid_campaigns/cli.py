import argparse
import json
import sys
from sendgrid import SendGridAPIClient
from .eml_extractor import extract_html_from_eml
from .campaign_manager import process_campaign_request

def main():
    parser = argparse.ArgumentParser(description="SendGrid Campaign Management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Extract HTML command
    extract_parser = subparsers.add_parser("extract-html", help="Extract HTML from an .eml file")
    extract_parser.add_argument("--json-config-file-path", required=True, help="Path to JSON config file")
    extract_parser.add_argument("--eml-file-path", required=True, help="Path to the input .eml file")
    extract_parser.add_argument("--html-body-file-path", required=True, help="Path to save the extracted HTML file")

    # Campaign Management command
    campaign_parser = subparsers.add_parser("campaign", help="Manage SendGrid campaigns")
    campaign_parser.add_argument("--json-config-file-path", required=True, help="Path to JSON config file")
    campaign_parser.add_argument("--campaign-id", help="Campaign ID for getting details or updating")
    campaign_parser.add_argument("--subject", help="Subject of the campaign")
    campaign_parser.add_argument("--sender", help="Sender email")
    campaign_parser.add_argument("--receivers-file-path", help="Path to receivers file (format: 'Full Name <email@domain.com>')")
    campaign_parser.add_argument("--html-body-file-path", help="Path to HTML body file")
    campaign_parser.add_argument("--scheduled-at", help="Scheduled send time (YYYY-MM-DD HH:MM:SS)")

    args = parser.parse_args()

    try:
        # Load config for both commands
        try:
            with open(args.json_config_file_path, "r") as config_file:
                config = json.load(config_file)
        except FileNotFoundError:
            print(f"Error: Config file not found at {args.json_config_file_path}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in config file {args.json_config_file_path}")
            sys.exit(1)

        if args.command == "extract-html":
            # Create dummy client with config
            client = type('Client', (), {'config': config})()
            html_file_path = extract_html_from_eml(client, args.eml_file_path, args.html_body_file_path)
            print(f"HTML content extracted to {html_file_path}")
            
        elif args.command == "campaign":
            if "SENDGRID_API_KEY" not in config:
                print("Error: SENDGRID_API_KEY must be present in the JSON config file")
                sys.exit(1)
                
            client = SendGridAPIClient(config["SENDGRID_API_KEY"])
            client.config = config  # Add config to client for Azure operations
            result = process_campaign_request(client, args)
            
            if isinstance(result, list):
                if not result:
                    print("\nNo campaigns found.")
                else:
                    print("\nCampaign List:")
                    for campaign in result:
                        print(f"\nCampaign ID: {campaign['campaign_id']}")
                        print(f"Subject: {campaign['subject']}")
                        print(f"Scheduled At: {campaign['scheduled_at']}")
                        print(f"From: {campaign['from']}")
            elif isinstance(result, dict):
                print("\nCampaign Details:")
                for key, value in result.items():
                    print(f"{key}: {value}")
            else:
                print(result)
                
    except ValueError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
