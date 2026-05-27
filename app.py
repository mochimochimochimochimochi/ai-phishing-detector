import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Phishing Detection Dashboard", page_icon="🛡️")

st.title("🛡️ Phishing Detection Dashboard")
st.caption("Real-time email phishing analysis results")

file_name = "phishing_results.xlsx"

if not os.path.exists(file_name):
    st.warning("No results yet. Run phishingpipeline.py to start analysing emails.")
else:
    df = pd.read_excel(file_name)

    # Summary stats
    total    = len(df)
    phishing = len(df[df['Verdict'] == 'PHISHING'])
    sus      = len(df[df['Verdict'] == 'SUSPICIOUS'])
    legit    = len(df[df['Verdict'] == 'LEGITIMATE'])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Emails", total)
    col2.metric("🚨 Phishing",   phishing)
    col3.metric("⚠️ Suspicious", sus)
    col4.metric("✅ Legitimate", legit)

    st.divider()

    # Filter
    filter_option = st.selectbox(
        "Filter by verdict:",
        ["All", "PHISHING", "SUSPICIOUS", "LEGITIMATE"]
    )

    if filter_option != "All":
        df = df[df['Verdict'] == filter_option]

    # Results table
    st.dataframe(
        df[['Sender', 'Subject', 'Verdict', 'Total Score', 'Explanation']],
        use_container_width=True
    )