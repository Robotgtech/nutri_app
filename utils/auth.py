import bcrypt
import streamlit as st

# -------------------------
# Password (bcrypt)
# -------------------------

def hash_password(password: str) -> str:
    pw = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw, salt)
    return hashed.decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    try:
        pw = password.encode("utf-8")
        hashed = password_hash.encode("utf-8")
        return bcrypt.checkpw(pw, hashed)
    except Exception:
        return False


# -------------------------
# Session / Auth (Streamlit)
# -------------------------

USER_KEY = "user"  # chave padrão da sessão

def is_logged_in() -> bool:
    return bool(st.session_state.get(USER_KEY))

def login_user(user: dict):
    """
    user deve conter APENAS dados seguros:
    ex: {"id": 1, "email": "x@email.com"}
    """
    st.session_state[USER_KEY] = user

def logout():
    """Limpa toda a sessão"""
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

def require_login(login_page: str = "pages/login.py"):
    """
    Chame no topo de TODA página protegida
    """
    if not is_logged_in():
        st.switch_page(login_page)

