import streamlit as st
from utils.bootstrap import bootstrap
from utils.db import get_patient, create_appointment, list_appointments, log_event
from datetime import date, time, datetime

st.set_page_config(page_title="Agenda", page_icon="📅", layout="wide")
bootstrap(show_patient_picker=True, require_login=True)

from utils.feedback_widget import feedback_widget
feedback_widget("Agenda")

st.title("📅 Agenda do Consultório")

# ✅ pega o user_id do padrão novo de sessão
user_id = st.session_state["user"]["id"]

pid = st.session_state.patient_id
if not pid:
    st.warning("Selecione um paciente na barra lateral.")
    st.stop()

p = get_patient(pid, user_id=user_id)
st.subheader(f"Agendar para: {p['nome']} (ID {p['id']})")

with st.form("agendar"):
    d = st.date_input("Data", value=date.today())
    h = st.time_input("Hora", value=time(8, 0))
    tipo = st.selectbox("Tipo", ["Consulta", "Retorno", "Reavaliação"])
    notas = st.text_area("Notas")
    ok = st.form_submit_button("Criar agendamento")

if ok:
    dt_iso = datetime.combine(d, h).isoformat()
    create_appointment(
        patient_id=pid,
        dt_iso=dt_iso,
        tipo=tipo,
        notas=(notas or "").strip(),
        user_id=user_id
    )

    log_event(
        user_id=uid,
        event_name="appointment_created",
        meta={
            "patient_id": pid,
            "dt_iso": dt_iso,
            "tipo": tipo
        }
    )

    st.success("Agendamento criado.")

st.divider()
st.subheader("Agenda (meus pacientes)")
appts = list_appointments(user_id=user_id)
st.dataframe(appts, use_container_width=True)

