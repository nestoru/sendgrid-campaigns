import os
import re
from email import message_from_file
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import base64
from azure.storage.blob import BlobServiceClient
import mimetypes
import hashlib
from datetime import datetime

class AzureStorageError(Exception):
    """Custom exception for Azure Storage operations"""
    pass

def get_azure_blob_url(config, blob_name):
    """Constructs the Azure CDN URL for a blob"""
    return f"https://{config['azure_cdn_storage_account_name']}.blob.core.windows.net/{config['azure_cdn_container_name']}/{config['azure_cdn_blob_path']}/{blob_name}"

def upload_to_azure(config, image_data, filename):
    """Uploads an image to Azure Blob Storage and returns its public URL"""
    try:
        connection_string = (
            f"DefaultEndpointsProtocol=https;"
            f"AccountName={config['azure_cdn_storage_account_name']};"
            f"AccountKey={config['azure_cdn_storage_account_key']};"
            f"EndpointSuffix=core.windows.net"
        )
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(config['azure_cdn_container_name'])
        
        # Construct blob path
        blob_path = f"{config['azure_cdn_blob_path']}/{filename}" if config['azure_cdn_blob_path'] else filename
        blob_client = container_client.get_blob_client(blob_path)
        
        # Upload the image
        blob_client.upload_blob(image_data, overwrite=True)
        return get_azure_blob_url(config, filename)
        
    except Exception as e:
        raise AzureStorageError(f"Failed to upload to Azure: {str(e)}")

def compress_image(image_data):
    """Compresses the image by reducing resolution if too large and applying JPEG compression"""
    try:
        image = Image.open(BytesIO(image_data))
        
        # Convert RGBA to RGB if needed
        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        
        # Reduce resolution if image is too large
        if image.width > 1200 or image.height > 1200:
            ratio = min(1200/image.width, 1200/image.height)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Save with compression
        output = BytesIO()
        image.save(output, format='JPEG', quality=60, optimize=True)
        output.seek(0)
        compressed_data = output.getvalue()
        
        print(f"Compressed image from {len(image_data)/1024:.1f}KB to {len(compressed_data)/1024:.1f}KB")
        return compressed_data
        
    except Exception as e:
        raise ValueError(f"Failed to compress image: {str(e)}")

def verify_azure_config(config):
    """Verifies that all required Azure configuration is present"""
    required_fields = [
        'azure_cdn_storage_account_name',
        'azure_cdn_storage_account_key',
        'azure_cdn_container_name'
    ]
    
    missing = [field for field in required_fields if not config.get(field)]
    if missing:
        raise ValueError(f"Missing required Azure configuration: {', '.join(missing)}")

def get_base_filename(html_file_path):
    """Generates a base filename from the HTML path"""
    base = os.path.splitext(os.path.basename(html_file_path))[0]
    sanitized = re.sub(r'[^\w\s-]', '_', base)
    sanitized = re.sub(r'[-\s]+', '_', sanitized)
    return sanitized.strip('_')

def process_image(img_tag, image_data, config, base_filename, index):
    """Processes a single image - compresses it, uploads to Azure, and updates the tag"""
    # Compress image
    compressed_data = compress_image(image_data['data'])
    
    # Generate unique filename using the base name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_hash = hashlib.md5(compressed_data).hexdigest()[:8]
    ext = mimetypes.guess_extension(image_data['type']) or '.jpg'
    filename = f"mail_campaigns/{base_filename}_{index}_{timestamp}_{file_hash}{ext}"
    
    # Upload and get URL
    cdn_url = upload_to_azure(config, compressed_data, filename)
    
    # Update image tag
    img_tag['src'] = cdn_url
    
    # Preserve dimensions but clean up other attributes
    if img_tag.get('width') and img_tag.get('height'):
        img_tag['style'] = f"width:{img_tag['width']}px;height:{img_tag['height']}px"
    
    allowed_attrs = ['src', 'alt', 'style']
    for attr in list(img_tag.attrs):
        if attr not in allowed_attrs:
            del img_tag[attr]
    
    return filename

def process_html_content(soup):
    """Add clicktracking=off to all links"""
    for a in soup.find_all('a'):
        a['clicktracking'] = 'off'
    return soup

def extract_html_from_eml(client, eml_file_path, html_body_file_path):
    """
    Extracts HTML from .eml file, uploads images to Azure CDN, and creates clean HTML
    
    Args:
        client: SendGrid client with Azure config
        eml_file_path: Path to source .eml file
        html_body_file_path: Path where to save the processed HTML
    
    Returns:
        str: Path to the generated HTML file
    """
    try:
        # Verify Azure configuration
        if not hasattr(client, 'config'):
            raise ValueError("SendGrid client must include Azure configuration")
        verify_azure_config(client.config)

        # Parse the email
        with open(eml_file_path, 'r') as eml_file:
            email_message = message_from_file(eml_file)

        # Extract HTML and image data
        html_content = None
        image_data = {}
        
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == 'text/html':
                    html_content = part.get_payload(decode=True).decode(part.get_content_charset())
                elif part.get_content_type().startswith('image/'):
                    content_id = part.get('Content-ID', '').strip('<>')
                    if content_id:
                        image_data[content_id] = {
                            'data': part.get_payload(decode=True),
                            'type': part.get_content_type()
                        }
        else:
            if email_message.get_content_type() == 'text/html':
                html_content = email_message.get_payload(decode=True).decode(email_message.get_content_charset())

        if not html_content:
            raise ValueError("No HTML content found in the email")

        # Get base filename for images
        base_filename = get_base_filename(html_body_file_path)

        # Process HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        soup = process_html_content(soup)
        processed_images = []
        image_count = 1
        
        # Handle each image
        for img in soup.find_all('img'):
            if img.get('src', '').startswith('cid:'):
                cid = img['src'].replace('cid:', '')
                if cid in image_data:
                    try:
                        filename = process_image(img, image_data[cid], client.config, base_filename, image_count)
                        processed_images.append(filename)
                        print(f"Processed image: {filename}")
                        image_count += 1
                    except Exception as e:
                        print(f"Failed to process image {cid}: {str(e)}")
                        continue

        # Create clean HTML
        clean_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
{soup.body.decode_contents() if soup.body else str(soup)}
</body>
</html>"""

        # Save the HTML
        os.makedirs(os.path.dirname(html_body_file_path), exist_ok=True)
        with open(html_body_file_path, 'w', encoding='utf-8') as f:
            f.write(clean_html)

        print(f"Generated HTML file at: {html_body_file_path}")
        print(f"Processed {len(processed_images)} images")
        return html_body_file_path
        
    except Exception as e:
        print(f"Error processing email: {str(e)}")
        raise
