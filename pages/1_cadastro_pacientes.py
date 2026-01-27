import streamlit as st
from datetime import date, datetime

from utils.bootstrap import bootstrap
from utils.db import create_patient, list_patients, get_patient, update_patient, log_event

st.set_page_config(page_title="Cadastro", page_icon="👤", layout="wide")
bootstrap(show_patient_picker=False, require_login=True)

from utils.feedback_widget import feedback_widget
feedback_widget("Cadastro de pacientes")

st.title("👤 Cadastro de Pacientes")

uid = st.session_state["user"]["id"]

patients = list_patients(user_id=uid)

modo = st.radio("Modo", ["Criar novo", "Editar existente"], horizontal=True)

selected_id = None
selected = None

if modo == "Editar existente":
    if not patients:
        st.info("Você ainda não tem pacientes cadastrados.")
        st.stop()

    opts = {f"{p['nome']} (ID {p['id']})": p["id"] for p in patients}
    label = st.selectbox("Selecione o paciente", list(opts.keys()))
    selected_id = opts[label]
    selected = get_patient(selected_id, user_id=uid)

    if not selected:
        st.error("Paciente não encontrado (ou você não tem acesso).")
        st.stop()

# defaults
nome0 = selected["nome"] if selected else ""
telefone0 = selected.get("telefone", "") if selected else ""
email0 = selected.get("email", "") if selected else ""
sexo0 = selected.get("sexo", "Masculino") if selected else "Masculino"
obs0 = selected.get("obs", "") if selected else ""

# nascimento: converter ISO -> date para o date_input
nasc0 = None
if selected and selected.get("nascimento"):
    try:
        nasc0 = datetime.fromisoformat(str(selected["nascimento"])).date()
    except Exception:
        nasc0 = None

with st.form("cadastro"):
    nome = st.text_input("Nome completo", value=nome0)
    telefone = st.text_input("Telefone", value=telefone0)
    email = st.text_input("E-mail", value=email0)

    nascimento = st.date_input(
        "Data de nascimento",
        value=nasc0 if nasc0 else date.today(),
        min_value=date(1900, 1, 1),
        max_value=date.today()
    )

    sexo = st.selectbox(
        "Sexo",
        ["Masculino", "Feminino", "Outro/Prefiro não informar"],
        index=["Masculino", "Feminino", "Outro/Prefiro não informar"].index(sexo0)
        if sexo0 in ["Masculino", "Feminino", "Outro/Prefiro não informar"] else 0
    )

    obs = st.text_area("Observações", value=obs0)

    ok = st.form_submit_button("Salvar")

if ok:
    if not nome.strip():
        st.error("Informe o nome.")
    else:
        try:
            if modo == "Criar novo":
                pid = create_patient(
                    nome=nome.strip(),
                    telefone=telefone.strip(),
                    email=email.strip(),
                    nascimento=str(nascimento),
                    sexo=sexo,
                    obs=obs.strip(),
                    user_id=uid
                )

                # ✅ LOG: paciente criado
                log_event(
                    user_id=uid,
                    event_name="patient_created",
                    meta={"patient_id": pid}
                )

                st.success(f"Paciente criado com ID {pid}.")
                st.session_state.patient_id = pid

            else:
                update_patient(
                    patient_id=selected_id,
                    user_id=uid,
                    nome=nome.strip(),
                    telefone=telefone.strip(),
                    email=email.strip(),
                    nascimento=nascimento,
                    sexo=sexo,
                    obs=obs.strip()
                )

                # ✅ LOG: paciente atualizado
                log_event(
                    user_id=uid,
                    event_name="patient_updated",
                    meta={"patient_id": selected_id}
                )

                st.success("Paciente atualizado!")
                st.session_state.patient_id = selected_id

        except Exception as e:
            log_event(
                user_id=uid,
                event_name="error",
                meta={
                    "page": "Cadastro de pacientes",
                    "action": "create_patient" if modo == "Criar novo" else "update_patient",
                    "error": str(e)
                }
            )
            st.error("Erro ao salvar paciente. Já registrei para correção.")

st.divider()
st.subheader("Pacientes cadastrados")

patients = list_patients(user_id=uid)
if patients:
    st.dataframe(patients, use_container_width=True)
else:
    st.caption("Nenhum paciente cadastrado ainda.")
