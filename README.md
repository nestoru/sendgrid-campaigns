# SendGrid Campaigns
A package to extract HTML from .eml files and manage SendGrid campaigns. It supports extracting HTML content and embedded images from email templates, uploading images to Azure CDN, and creating/managing SendGrid marketing campaigns.

Uses poetry for dependency management and packaging.

## Features
- Extract HTML and images from .eml files
- Upload images to Azure CDN for email compatibility
- Create and manage SendGrid marketing campaigns
- Schedule campaign sending
- Manage contact lists and suppression groups
- Handle email templates with embedded images

## Prerequisites
- Poetry installed (e.g., for OSX: `brew install pipx && pipx ensurepath && pipx install poetry`)
- Azure Storage account for image hosting
- SendGrid API key with Marketing Campaigns access
- Python 3.9+

## Configuration
Required `.config.json` file:
```json
{
  "SENDGRID_API_KEY": "your_sendgrid_api_key",
  "azure_cdn_storage_account_type": "azure",
  "azure_cdn_storage_account_name": "your_storage_account",
  "azure_cdn_storage_account_key": "your_storage_key",
  "azure_cdn_container_name": "your_container",
  "azure_cdn_blob_path": "mail_campaigns"
}
```

## Installation and Environment
```bash
# Install dependencies
poetry install

# Activate the poetry environment
poetry shell
```

## Usage

### Extract HTML from Email Template
```bash
sendgrid-campaigns extract-html --json-config-file-path .config.json --eml-file-path template.eml --html-body-file-path output.html
```

### Create Campaign
```bash
sendgrid-campaigns campaign --json-config-file-path .config.json \
  --subject "Campaign Subject" \
  --sender "sender@domain.com" \
  --receivers-file-path receivers.txt \
  --html-body-file-path campaign.html \
  --scheduled-at "2024-11-20 21:11:00"
```

### List Campaigns
```bash
sendgrid-campaigns campaign --json-config-file-path .config.json
```

### Get Campaign Details
```bash
sendgrid-campaigns campaign --json-config-file-path .config.json --campaign-id <campaign_id>
```

## Project Structure
```
.
├── README.md
├── pyproject.toml
└── sendgrid_campaigns
    ├── __init__.py
    ├── api
    │   ├── campaign.py    # SendGrid campaign API operations
    │   ├── scheduling.py  # Campaign scheduling
    │   └── sender.py      # Sender management
    ├── campaign_manager.py # Campaign creation/management
    ├── cli.py             # Command line interface
    ├── eml_extractor.py   # HTML/image extraction
    └── utils
        ├── date_utils.py  # Date handling
        └── file_utils.py  # File operations
```

## Contributing
Add dependencies using poetry:
```bash
poetry add package_name
```

## License
MIT

## Author
Nestor Urquiza <nestor.urquiza@gmail.com>
