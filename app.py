import streamlit as st
import joblib
import anthropic
import re
from pathlib import Path

st.set_page_config(page_title="Phishing Email Checker", page_icon="🛡️")

st.title("🛡️ Phishing Email Checker")
st.caption("Paste a suspicious email below and we'll analyse it for you.")

# ============================================================
# LOAD MODEL
# ============================================================
HERE       = Path(__file__).parent
MODEL_PATH = HERE / 'phishing_model.joblib'
model      = joblib.load(MODEL_PATH)

ANTHROPIC_API_KEY =  st.secrets["ANTHROPIC_API_KEY"]  # replace locally, not on GitHub
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

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
# UI
# ============================================================
email_input = st.text_area(
    "Paste the email content here:",
    height=300,
    placeholder="Copy and paste the full email text here..."
)

if st.button("🔍 Analyse Email"):
    if email_input.strip():
        with st.spinner("Analysing..."):
            score       = hybrid_phishing_score(email_input, model)
            explanation = explain_verdict(email_input, score)

        verdict = score['verdict']
        if verdict == 'PHISHING':
            st.error(f"🚨 VERDICT: {verdict}")
        elif verdict == 'SUSPICIOUS':
            st.warning(f"⚠️ VERDICT: {verdict}")
        else:
            st.success(f"✅ VERDICT: {verdict}")

        col1, col2, col3 = st.columns(3)
        col1.metric("ML Score",    f"{score['ml_score']} / 60")
        col2.metric("Rule Score",  f"{score['rule_score']} / 40")
        col3.metric("Total Score", f"{score['total_score']} / 100")

        st.divider()
        st.subheader("💬 AI Explanation")
        st.write(explanation)

    else:
        st.warning("Please paste an email first.")