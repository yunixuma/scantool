import os
import smtplib
import ssl
import base64
import csv, yaml
from sys import path
import argparse
from dotenv import load_dotenv
from email.message import EmailMessage
from email.utils import make_msgid
import my_common as my

def load_smtp_config(config_path: str) -> dict:
    """
    Load SMTP configuration from .env file
    """
    load_dotenv(dotenv_path=config_path)
    config = {
        "server": os.environ.get("SMTP_SERVER"),
        "port": int(os.environ.get("SMTP_PORT", 465)),
        "user": os.environ.get("SMTP_USER"),
        "password": os.environ.get("SMTP_PASSWORD"),
    }
    if not all(config.values()):
        raise ValueError("Incomplete SMTP configuration in .env file")
    return config

def build_message(template, row):
    """
    Build an email message from template and CSV row data
    1. Set headers (Subject, To, From, Bcc)
    2. Merge body with placeholders
    3. Determine if HTML email and handle embedded image if present
    4. Return EmailMessage object
    """
    msg = EmailMessage()

    # 1. Set headers
    msg['Subject'] = template.get('subject', 'No Subject')
    msg['From'] = template.get('from', '')
    msg['Bcc'] = template.get('bcc', '')
    # Get To address from CSV row
    if not row.get('To'):
        print("Error: 'To' address is missing in CSV row.")
        return None
    msg['To'] = row['To']
    print(f"  -> From: {msg['From']}, To: {row.get('To', '')}, Subject: {msg['Subject']}")

    # 2. Merge body with placeholders
    body = template.get('body', '')
    # .get(col, '') to avoid KeyError if column missing
    for column_name, value in row.items():
        # 'From' and 'image' are not placeholders to replace
        if column_name.lower() in ['from', 'image']:
            continue            
        # Construct the placeholder
        placeholder = f"{{{column_name}}}"
        # Replace all occurrences of the placeholder in the body
        body = body.replace(placeholder, str(value or ''))

    # 3. Determine if HTML email and handle embedded image if present
    image_b64 = row.get('image', '')
    html_tags = ['<html', '<br', '<p', '<div', '<img']
    is_html = any(tag in body.lower() for tag in html_tags) or image_b64

    image_cid = None
    image_data = None

    if image_b64:
        try:
            image_data = base64.b64decode(image_b64)
            # Generate a unique Content-ID for the image
            image_cid = make_msgid(domain="").strip('<>')
            # Replace placeholder in body with CID reference
            body = body.replace('{image_cid}', image_cid)
        except Exception as e:
            print(f"  -> Error decoding base64 image: {e}")
            image_b64 = None # Reset to avoid embedding

    if is_html:
        # As HTML email
        msg.set_content("This is an HTML email. Please enable HTML to view it.")

        # Embed image if available
        if image_b64 and image_cid and image_data:
            msg.add_related(image_data, 'image', 'png', cid=f'<{image_cid}>')

        msg.add_alternative(body, subtype='html')

    else:
        # As plain text email
        msg.set_content(body)
        
    return msg

def send_email(smtp_config, message):
    """
    Connect SMTP server and send an email message
    """
    context = ssl.create_default_context()
    
    try:
        with smtplib.SMTP_SSL(smtp_config["server"], smtp_config["port"], context=context) as server:
        # with smtplib.SMTP(smtp_config["server"], smtp_config["port"], 
        #         local_hostname="localhost") as server:
        #     server.starttls(context=context)

            server.login(smtp_config["user"], smtp_config["password"])
            server.send_message(message)
            print(f"  -> Success: To: {message['To']}, Subject: {message['Subject']}")
    except smtplib.SMTPException as e:
        print(f"  -> Failure: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Send emails using a template and CSV data for merge")

    parser.add_argument(
        "merge_data",
        type=str,
        help="File path to CSV data for email merge"
    )

    parser.add_argument(
        "-t", "--template",
        type=str,
        default="mail_template.yaml",
        help="Email template file (YAML format). Default: mail_template.yaml"
    )

    parser.add_argument(
        "-c", "--config",
        type=str,
        default=".env",
        help="SMTP config file (.env format). Default: .env"
    )
    args = parser.parse_args()

    try:
        smtp_config = load_smtp_config(args.config)
        mail_template = my.load_yaml(args.template)
        merge_data = my.load_csv(args.merge_data)
    except Exception as e:
        print(f"Error occurred during setup: {e}")
        return

    print(f"Start processing {len(merge_data)} of email records...") 
    
    for i, row in enumerate(merge_data):
        print(f"Processing... ({i+1}/{len(merge_data)})")
        
        try:
            msg = build_message(mail_template, row)
            if msg:
                send_email(smtp_config, msg)
        except Exception as e:
            print(f"  -> Error processing row {i+1} : {e}")
            
    print("All done.")

if __name__ == "__main__":
    main()