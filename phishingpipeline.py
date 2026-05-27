import imaplib
import smtplib
import email
import time
import re
import os
import joblib
import anthropic
import pandas as pd
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ============================================================
# CREDENTIALS
# ============================================================
EMAIL             = "PhishermanTP@gmail.com"
PASSWORD          = "fdhh nvdo eddt kjex"  # your app password
ANTHROPIC_API_KEY = "REPLACE_WITH_YOUR_KEY" # hide api key

# ============================================================
# LOAD MODEL
# ============================================================
model  = joblib.load("phishing_model.joblib")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
print("✅ Model and Claude client loaded.")

# ============================================================
# ML SCORING
# ============================================================
def hybrid_phishing_score(email_text, ml_model):
    ml_prob  = float(ml_model.predict_proba([email_text])[0][1])
    ml_score = ml_prob * 60

    rule_score = 0
    text_lower = email_text.lower()
    rules = {
        'urgent action required': 10, 'verify your account': 10,
        'click here': 8,              'password': 7,
        'bank account': 8,            'limited time': 6,
        'congratulations you won': 10,'suspend': 7,
        'unusual activity': 8,
    }
    for phrase, score in rules.items():
        if phrase in text_lower:
            rule_score += score
    if re.search(r'http[s]?://', text_lower):
        rule_score += 10
    rule_score = min(rule_score, 40)

    total_score = ml_score + rule_score
    if total_score >= 60:   verdict = 'PHISHING'
    elif total_score >= 35: verdict = 'SUSPICIOUS'
    else:                   verdict = 'LEGITIMATE'

    return {
        'ml_probability': round(ml_prob, 3),
        'ml_score':       round(ml_score, 1),
        'rule_score':     round(rule_score, 1),
        'total_score':    round(total_score, 1),
        'verdict':        verdict
    }

# ============================================================
# CLAUDE AI EXPLANATION
# ============================================================
def explain_verdict(email_text, score_result):
    prompt = f"""
    An email was analysed by a phishing detection system and scored as: {score_result['verdict']}
    ML probability: {score_result['ml_probability']}
    Rule-based score: {score_result['rule_score']}

    Email content:
    {email_text[:500]}

    In 2-3 sentences, explain to a non-technical user why this email
    was flagged or cleared. Be specific about what triggered the score.
    """
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

# ============================================================
# SEND REPLY VIA GMAIL
# ============================================================
def send_reply(to_address, original_subject, score_result, explanation):
    verdict = score_result['verdict']
    if verdict == 'PHISHING':     emoji = '🚨'
    elif verdict == 'SUSPICIOUS': emoji = '⚠️'
    else:                         emoji = '✅'

    body = f"""Hello,

Your reported email has been analysed by our Phishing Detection System.

{emoji} VERDICT: {verdict}

--- Score Breakdown ---
ML Score    : {score_result['ml_score']} / 60
Rule Score  : {score_result['rule_score']} / 40
Total Score : {score_result['total_score']} / 100

--- AI Explanation ---
{explanation}

---
This is an automated response from the Phishing Detection System.
Do not reply to this email.
"""
    msg = MIMEMultipart()
    msg['From']    = EMAIL
    msg['To']      = to_address
    msg['Subject'] = f"Phishing Analysis Result: {verdict} — Re: {original_subject}"
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL, PASSWORD)
        smtp.sendmail(EMAIL, to_address, msg.as_string())

    print(f"📧 Reply sent to {to_address}")

# ============================================================
# PROCESS NEW EMAILS
# ============================================================
def process_new_emails():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL, PASSWORD)
    mail.select("inbox")

    status, messages = mail.search(None, "UNSEEN")
    email_ids = messages[0].split()

    if not email_ids:
        print("No new emails.")
        mail.logout()
        return

    print(f"📬 {len(email_ids)} new email(s) found.")

    for e_id in email_ids:
        status, msg_data = mail.fetch(e_id, "(RFC822)")

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                # Extract subject
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")

                # Extract sender
                sender = msg.get("From")

                # Extract body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
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

                email_text = subject + ' ' + body

                print(f"\n📨 From   : {sender}")
                print(f"   Subject: {subject[:60]}")

                # Run ML + AI
                score       = hybrid_phishing_score(email_text, model)
                explanation = explain_verdict(email_text, score)

                print(f"   Verdict: {score['verdict']} (score: {score['total_score']})")

                # Send reply
                send_reply(sender, subject, score, explanation)

                # Log to Excel
                file_name = "phishing_results.xlsx"
                new_row = pd.DataFrame([{
                    "Sender":      sender,
                    "Subject":     subject,
                    "Body":        body[:1000],
                    "Verdict":     score['verdict'],
                    "ML Score":    score['ml_score'],
                    "Rule Score":  score['rule_score'],
                    "Total Score": score['total_score'],
                    "Explanation": explanation
                }])
                if os.path.exists(file_name):
                    old_df = pd.read_excel(file_name)
                    new_row = pd.concat([old_df, new_row], ignore_index=True)
                new_row.to_excel(file_name, index=False)
                print(f"💾 Logged to {file_name}")

                time.sleep(2)

    mail.logout()

# ============================================================
# RUN CONTINUOUSLY
# ============================================================
print("🛡️  Phishing detection system running.")
print("Checking for new emails every 60 seconds...")
print("Press Ctrl+C to stop.\n")

while True:
    try:
        process_new_emails()
    except Exception as e:
        print(f"❌ Error: {e}")
    time.sleep(300)
