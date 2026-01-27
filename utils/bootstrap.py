import streamlit as st
from utils.db import init_db, list_patients
from utils.auth import is_logged_in, logout

def bootstrap(show_patient_picker: bool = True, require_login: bool = True):
    init_db()

    # Garantir chaves básicas (opcional, mas ok)
    if "patient_id" not in st.session_state:
        st.session_state.patient_id = None

    st.sidebar.title("🥗 NutriApp")

    # --------- Proteção (login) ----------
    if require_login and not is_logged_in():
        st.sidebar.warning("Faça login para acessar.")
        st.switch_page("pages/0_Login.py")
        st.stop()

    # --------- Sidebar: usuário + logout ----------
    if is_logged_in():
        st.sidebar.caption(f'Logado como: {st.session_state["user"]["email"]}')
        st.sidebar.button("Sair", on_click=logout)

    # --------- Seletor de paciente ----------
    if not show_patient_picker:
        return

    if not is_logged_in():
        # Se a página não exige login e não está logado, não mostra seletor.
        st.session_state.patient_id = None
        return

    user_id = st.session_state["user"]["id"]
    patients = list_patients(user_id=user_id)

    if not patients:
        st.sidebar.info("Nenhum paciente cadastrado ainda.")
        st.session_state.patient_id = None
        return

    options = {f'{p["nome"]} (ID {p["id"]})': p["id"] for p in patients}
    labels = list(options.keys())

    default_idx = 0
    if st.session_state.patient_id in options.values():
        for i, lab in enumerate(labels):
            if options[lab] == st.session_state.patient_id:
                default_idx = i
                break

    chosen = st.sidebar.selectbox("Paciente selecionado", labels, index=default_idx)
    st.session_state.patient_id = options[chosen]

