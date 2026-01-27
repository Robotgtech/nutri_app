import streamlit as st
from datetime import date

from utils.bootstrap import bootstrap
from utils.db import get_patient, create_assessment, get_last_assessment, log_event

st.set_page_config(page_title="Avaliação", page_icon="📋", layout="wide")

# Avaliação usa o seletor global de paciente
bootstrap(show_patient_picker=True)

from utils.feedback_widget import feedback_widget
feedback_widget("Avaliação")

st.title("📋 Avaliação Nutricional")

pid = st.session_state.patient_id
if not pid:
    st.warning("Selecione um paciente na barra lateral.")
    st.stop()

uid = st.session_state["user"]["id"]
patient = get_patient(pid, user_id=uid)

st.subheader(f"Paciente: {patient['nome']} (ID {patient['id']})")

last = get_last_assessment(pid)
if last:
    st.caption("Última avaliação registrada:")
    st.json(last)

with st.form("avaliacao"):
    col1, col2 = st.columns(2)

    with col1:
        peso = st.number_input(
            "Peso (kg)", min_value=1.0, step=0.1,
            value=float(last["peso"]) if last and last.get("peso") else 70.0
        )
        altura_cm = st.number_input(
            "Altura (cm)", min_value=50.0, step=0.5,
            value=float(last["altura_cm"]) if last and last.get("altura_cm") else 170.0
        )

    with col2:
        cintura_cm = st.number_input(
            "Cintura (cm)", min_value=0.0, step=0.5,
            value=float(last["cintura_cm"]) if last and last.get("cintura_cm") else 0.0
        )
        quadril_cm = st.number_input(
            "Quadril (cm)", min_value=0.0, step=0.5,
            value=float(last["quadril_cm"]) if last and last.get("quadril_cm") else 0.0
        )

    objetivo = st.selectbox("Objetivo", ["Emagrecimento", "Ganho de massa", "Manutenção", "Performance/saúde"])
    atividade = st.selectbox("Nível de atividade", ["Sedentário", "Leve", "Moderado", "Alto", "Muito alto"])
    sono_h = st.number_input(
        "Sono (h/dia)", min_value=0.0, max_value=24.0, step=0.5,
        value=float(last["sono_h"]) if last and last.get("sono_h") else 7.0
    )
    obs = st.text_area("Observações", value=(last.get("obs", "") if last else ""))

    ok = st.form_submit_button("Salvar avaliação")

if ok:
    uid = st.session_state["user"]["id"]

    try:
        assessment_id = create_assessment(
            pid,
            {
                "data_iso": date.today().isoformat(),
                "peso": float(peso),
                "altura_cm": float(altura_cm),
                "cintura_cm": float(cintura_cm),
                "quadril_cm": float(quadril_cm),
                "objetivo": objetivo,
                "atividade": atividade,
                "sono_h": float(sono_h),
                "obs": obs.strip(),
            },
            user_id=uid
        )

        # ✅ LOG de sucesso
        log_event(
            user_id=uid,
            event_name="assessment_created",
            meta={
                "patient_id": pid,
                "assessment_id": assessment_id
            }
        )

        st.success("Avaliação salva com sucesso!")

    except Exception as e:
        # ✅ LOG de erro real
        log_event(
            user_id=uid,
            event_name="error",
            meta={
                "page": "Avaliação Nutricional",
                "action": "create_assessment",
                "error": str(e)
            }
        )
        st.error("Erro ao salvar avaliação. Já registrei para correção.")

