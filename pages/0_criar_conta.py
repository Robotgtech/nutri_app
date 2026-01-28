import streamlit as st
from utils.bootstrap import bootstrap
from utils.db import get_user_by_email, create_user, is_email_allowed
from utils.auth import hash_password, login_user

st.set_page_config(page_title="Criar conta", page_icon="🧾", layout="wide")

bootstrap(show_patient_picker=False, require_login=False)

st.title("🧾 Criar conta (Nutricionista)")

with st.form("signup", clear_on_submit=False):
    email_raw = st.text_input("E-mail", placeholder="seu@email.com")
    password = st.text_input("Senha", type="password")
    password2 = st.text_input("Confirmar senha", type="password")
    ok = st.form_submit_button("Criar conta")

if ok:
    email = (email_raw or "").strip().lower()

    if not email or "@" not in email:
        st.error("Informe um e-mail válido.")
    elif len(password or "") < 8:
        st.error("Senha muito curta. Use pelo menos 8 caracteres.")
    elif password != password2:
        st.error("As senhas não conferem.")
    else:
        # 🔒 Beta fechada: só cria conta se o email estiver liberado
        if not is_email_allowed(email):
            st.error("Acesso restrito à versão beta. Solicite convite.")
            st.stop()

        existing = get_user_by_email(email)
        if existing:
            st.error("Esse e-mail já está cadastrado.")
        else:
            user_id = create_user(email=email, password_hash=hash_password(password))

            # ✅ login automático no padrão novo
            login_user({"id": user_id, "email": email})

            st.success("Conta criada e login realizado!")
            st.switch_page("app.py")


st.divider()
if st.button("Voltar para Login"):
    st.switch_page("pages/0_login.py")
