import streamlit as st
from pathlib import Path

from utils.bootstrap import bootstrap
from utils.db import get_patient, get_last_assessment, get_last_diet, list_diet_items, log_event
from utils.pdf_report import build_pdf


st.set_page_config(page_title="Relatório PDF", page_icon="🧾", layout="wide")
bootstrap(show_patient_picker=True, require_login=True)

from utils.feedback_widget import feedback_widget
feedback_widget("Relatório")

st.title("🧾 Relatório do Paciente (PDF)")

pid = st.session_state.patient_id
if not pid:
    st.warning("Selecione um paciente na barra lateral.")
    st.stop()

uid = st.session_state["user"]["id"]

diet = get_last_diet(pid, user_id=uid)
diet_id = diet["id"] if diet else None
diet_items = list_diet_items(uid, pid, diet_id=diet_id)
patient = get_patient(pid, user_id=uid)
if not patient:
    st.error("Paciente não encontrado (ou você não tem acesso).")
    st.stop()

assessment = get_last_assessment(pid, user_id=uid)
diet = get_last_diet(pid, user_id=uid)

st.subheader(f"Paciente: {patient['nome']} (ID {patient['id']})")

col1, col2 = st.columns(2)
with col1:
    st.write("Última avaliação:")
    st.json(assessment if assessment else {"info": "Sem avaliação registrada"})
with col2:
    st.write("Última dieta:")
    st.json(diet if diet else {"info": "Sem dieta registrada"})

st.divider()

out_dir = Path("data")
out_dir.mkdir(exist_ok=True)
pdf_path = out_dir / f"relatorio_paciente_{patient['id']}.pdf"

if st.button("Gerar PDF agora"):
    try:
        build_pdf(str(pdf_path), patient, assessment, diet, diet_items)

        # ✅ LOG de sucesso
        log_event(
            user_id=uid,
            event_name="pdf_generated",
            meta={
                "patient_id": pid,
                "diet_id": diet_id
            }
        )

        st.success("PDF gerado com sucesso!")

    except Exception as e:
        # ✅ LOG de erro real
        log_event(
            user_id=uid,
            event_name="error",
            meta={
                "page": "Relatório",
                "action": "build_pdf",
                "error": str(e)
            }
        )
        st.error("Ocorreu um erro ao gerar o relatório. Já registrei para correção.")


if pdf_path.exists():
    with open(pdf_path, "rb") as f:
        st.download_button(
            "📄 Baixar relatório em PDF",
            data=f,
            file_name=pdf_path.name,
            mime="application/pdf"
        )
