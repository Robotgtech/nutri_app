import streamlit as st
from utils.bootstrap import bootstrap
from utils.db import list_feedback

st.set_page_config(page_title="Admin - Feedback", page_icon="🛠️", layout="wide")
bootstrap(show_patient_picker=False, require_login=True)

st.title("🛠️ Feedback (beta)")

items = list_feedback(limit=300)
if not items:
    st.info("Ainda não há feedback.")
else:
    st.dataframe(items, use_container_width=True)
