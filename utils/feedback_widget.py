import streamlit as st
from utils.db import create_feedback

def feedback_widget(page_name: str):
    if "user" not in st.session_state:
        return

    user_id = st.session_state["user"]["id"]

    with st.sidebar.expander("💬 Enviar feedback", expanded=False):
        rating = st.slider("Nota (0–10)", 0, 10, 8)
        msg = st.text_area("O que você gostaria de melhorar?", height=120)
        if st.button("Enviar", key=f"send_feedback_{page_name}"):
            if not (msg or "").strip():
                st.warning("Escreva uma mensagem antes de enviar.")
            else:
                create_feedback(user_id=user_id, page=page_name, message=msg, rating=rating)
                st.success("Feedback enviado! ✅")
                st.rerun()
