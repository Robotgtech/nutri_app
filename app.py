import streamlit as st
from utils.bootstrap import bootstrap

from utils.feedback_widget import feedback_widget
feedback_widget("Home")

st.set_page_config(page_title="NutriApp", page_icon="🥗", layout="wide")
bootstrap(show_patient_picker=False, require_login=True)

st.title("🥗 NutriApp")
st.write("Bem-vindo! Use o menu à esquerda para navegar.")

st.markdown("""
### O que você consegue fazer aqui:
- ✅ Cadastro de pacientes
- ✅ Agenda do consultório
- ✅ Avaliação nutricional
- ✅ Cálculo da dieta
- ✅ Relatório completo (com PDF)
""")

st.info("Dica: cada item do menu está em um arquivo dentro da pasta `pages/`.")