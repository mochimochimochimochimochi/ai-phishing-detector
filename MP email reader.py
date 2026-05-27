import imaplib
import email
from email.header import decode_header
import pandas as pd
import re

def contains_url(text):
    if not text:
        return 0
    url_pattern = r"http[s]?://|www\."
    return 1 if re.search(url_pattern, text) else 0

# Gmail credentials
EMAIL = "PhishermanTP@gmail.com"
PASSWORD = "fdhh nvdo eddt kjex"

# Connect to Gmail
mail = imaplib.IMAP4_SSL("imap.gmail.com")

# Login
mail.login(EMAIL, PASSWORD)

# Open inbox
mail.select("inbox")

# Search all emails
status, messages = mail.search(None, "ALL")

email_ids = messages[0].split()

data = []

# Read latest 10 emails
for e_id in email_ids[-10:]:

    status, msg_data = mail.fetch(e_id, "(RFC822)")

    for response_part in msg_data:

        if isinstance(response_part, tuple):

            msg = email.message_from_bytes(response_part[1])

            # Extract subject
            subject, encoding = decode_header(msg["Subject"])[0]

            if isinstance(subject, bytes):
                subject = subject.decode(
                    encoding if encoding else "utf-8"
                )

            # Extract sender
            sender = msg.get("From")

            # Extract date
            date = msg.get("Date")

            # Extract body
            body = ""

            if msg.is_multipart():

                for part in msg.walk():

                    content_type = part.get_content_type()
                    content_disposition = str(
                        part.get("Content-Disposition")
                    )

                    try:
                        payload = part.get_payload(decode=True)

                        if payload:
                            body = payload.decode()

                    except:
                        pass

            else:

                payload = msg.get_payload(decode=True)

                if payload:
                    body = payload.decode()

            # Save into list
            data.append({
                "Sender": sender,
                "Subject": subject,
                "Date": date,
                "Body": body[:5000],
                "has_url": contains_url(subject + str(body))
                
            })

# Create Excel file
df = pd.DataFrame(data)

import os
import pandas as pd

file_name = "emails.xlsx"

# If file exists → load and append
if os.path.exists(file_name):
    old_df = pd.read_excel(file_name)
    df = pd.concat([old_df, df], ignore_index=True)

# Save back (overwrite updated file)
df.to_excel(file_name, index=False)
print("Emails saved to emails.xlsx")