import streamlit as st
from utils.bootstrap import bootstrap
from utils.db import (
    get_patient,
    create_appointment,
    list_appointments,
    update_appointment,
    delete_appointment,
    log_event,
)
from utils.feedback_widget import feedback_widget
from datetime import date, time, datetime

st.set_page_config(page_title="Agenda", page_icon="📅", layout="wide")
bootstrap(show_patient_picker=True, require_login=True)

feedback_widget("Agenda")
st.title("📅 Agenda do Consultório")

user_id = st.session_state["user"]["id"]

pid = st.session_state.patient_id
if not pid:
    st.warning("Selecione um paciente na barra lateral.")
    st.stop()

p = get_patient(pid, user_id=user_id)
st.subheader(f"Agendar para: {p['nome']} (ID {p['id']})")

# -----------------------------
# Criar agendamento
# -----------------------------
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
        user_id=user_id,
    )

    log_event(
        user_id=user_id,
        event_name="appointment_created",
        meta={"patient_id": pid, "dt_iso": dt_iso, "tipo": tipo},
    )

    st.success("Agendamento criado.")
    st.rerun()

st.divider()

# -----------------------------
# Listar / editar / apagar
# -----------------------------
st.subheader("Agenda (meus pacientes)")
appts = list_appointments(user_id=user_id)

if not appts:
    st.info("Nenhum agendamento ainda.")
    st.stop()

st.dataframe(appts, use_container_width=True)

# Seletor de agendamento
# (appts é lista de dict; cada item deve ter pelo menos 'id' e 'dt_iso')
options = {}
for a in appts:
    # tenta usar patient_nome se existir
    patient_nome = a.get("patient_nome") or f"Paciente {a.get('patient_id','?')}"
    label = f'#{a["id"]} — {a["dt_iso"]} — {patient_nome} — {a.get("tipo","")}'
    options[label] = a["id"]

st.subheader("Editar ou apagar agendamento")
chosen_label = st.selectbox("Selecione um agendamento", list(options.keys()))
chosen_id = options[chosen_label]

# pega o agendamento escolhido (pra preencher o form)
selected = next(a for a in appts if a["id"] == chosen_id)

# parse dt_iso
try:
    dt = datetime.fromisoformat(selected["dt_iso"])
    default_d = dt.date()
    default_h = dt.time().replace(second=0, microsecond=0)
except Exception:
    default_d = date.today()
    default_h = time(8, 0)

with st.form("editar_agendamento"):
    new_d = st.date_input("Nova data", value=default_d)
    new_h = st.time_input("Nova hora", value=default_h)
    new_tipo = st.selectbox(
        "Novo tipo",
        ["Consulta", "Retorno", "Reavaliação"],
        index=["Consulta", "Retorno", "Reavaliação"].index(selected.get("tipo", "Consulta"))
        if selected.get("tipo") in ["Consulta", "Retorno", "Reavaliação"]
        else 0,
    )
    new_notas = st.text_area("Novas notas", value=(selected.get("notas") or ""))

    c1, c2 = st.columns(2)
    with c1:
        salvar = st.form_submit_button("Salvar alterações")
    with c2:
        apagar = st.form_submit_button("Apagar agendamento")

if salvar:
    new_dt_iso = datetime.combine(new_d, new_h).isoformat()
    update_appointment(
        appointment_id=chosen_id,
        user_id=user_id,
        dt_iso=new_dt_iso,
        tipo=new_tipo,
        notas=(new_notas or "").strip(),
    )

    log_event(
        user_id=user_id,
        event_name="appointment_updated",
        meta={"appointment_id": chosen_id, "dt_iso": new_dt_iso, "tipo": new_tipo},
    )

    st.success("Agendamento atualizado.")
    st.rerun()

if apagar:
    delete_appointment(chosen_id, user_id)

    log_event(
        user_id=user_id,
        event_name="appointment_deleted",
        meta={"appointment_id": chosen_id},
    )

    st.success("Agendamento apagado.")
    st.rerun()