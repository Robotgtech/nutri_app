import streamlit as st
from utils.bootstrap import bootstrap
from utils.db import get_user_by_email, is_email_allowed
from utils.auth import verify_password, login_user

st.set_page_config(page_title="Login", page_icon="🔐", layout="wide")

# Login NÃO exige login, óbvio :)
bootstrap(show_patient_picker=False, require_login=False)

st.title("🔐 Login")

with st.form("login", clear_on_submit=False):
    email_raw = st.text_input("E-mail", placeholder="seu@email.com")
    password = st.text_input("Senha", type="password")
    ok = st.form_submit_button("Entrar")

if ok:
    email = (email_raw or "").strip().lower()

    if not email or not password:
        st.error("Informe e-mail e senha.")
    else:
        # 🔒 BETA FECHADA: bloqueia login se email não estiver liberado
        if not is_email_allowed(email):
            st.error("Seu acesso ainda não foi liberado para a versão beta.")
            st.stop()

        user = get_user_by_email(email)

        # Mensagem genérica por segurança
        if not user or not verify_password(password, user["password_hash"]):
            st.error("E-mail ou senha inválidos.")
        else:
            # ✅ Guarda na sessão um dict seguro (padrão)
            login_user({"id": user["id"], "email": user["email"]})

            st.success("Login realizado!")
            st.switch_page("app.py")

st.divider()
st.caption("Ainda não tem conta?")
if st.button("Criar conta"):
    st.switch_page("pages/0_criar_conta.py")


