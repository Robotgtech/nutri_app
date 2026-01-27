import streamlit as st
from datetime import datetime, date

from utils.bootstrap import bootstrap
from utils.db import get_patient, get_last_assessment, create_diet, get_last_diet
from utils.formulas import mifflin_st_jeor, tdee, macros_por_calorias

st.set_page_config(page_title="Dieta", page_icon="🧮", layout="wide")
bootstrap(show_patient_picker=True, require_login=True)

from utils.feedback_widget import feedback_widget
feedback_widget("Cálculo dieta")

def calc_idade(nascimento_iso: str) -> int | None:
    if not nascimento_iso:
        return None
    try:
        nasc = datetime.fromisoformat(str(nascimento_iso)).date()
        hoje = date.today()
        idade = hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))
        return max(0, idade)
    except Exception:
        return None

st.title("🧮 Cálculo da Dieta")

uid = user_id = st.session_state["user"]["id"]
pid = st.session_state.patient_id
if not pid:
    st.warning("Selecione um paciente na barra lateral.")
    st.stop()

patient = get_patient(pid, user_id=uid)
if not patient:
    st.error("Paciente não encontrado (ou você não tem acesso).")
    st.stop()

st.subheader(f"Paciente: {patient['nome']} (ID {patient['id']})")
st.caption(f"Nascimento (ISO no banco): {patient.get('nascimento','')}")

# Puxa última avaliação (do usuário)
last_assessment = get_last_assessment(pid, user_id=uid)
if last_assessment:
    st.caption("Estou puxando peso/altura da última avaliação (você pode alterar).")
else:
    st.caption("Sem avaliação registrada — preencha manualmente.")

# Sexo default vindo do cadastro
sexo_default = patient.get("sexo", "Masculino")
if sexo_default not in ["Masculino", "Feminino"]:
    sexo_default = "Masculino"
sexo_idx = 0 if sexo_default == "Masculino" else 1

col1, col2 = st.columns(2)
with col1:
    idade_auto = calc_idade(patient.get("nascimento"))
    if idade_auto is None:
        st.caption("Sem data de nascimento válida no cadastro — informe a idade manualmente.")
        idade_auto = 30

    idade = st.number_input("Idade", min_value=1, max_value=120, step=1, value=int(idade_auto))

    sexo = st.selectbox(
        "Sexo (para fórmula)",
        ["Masculino", "Feminino"],
        index=sexo_idx
    )

with col2:
    peso_default = float(last_assessment["peso"]) if last_assessment and last_assessment.get("peso") else 70.0
    altura_default = float(last_assessment["altura_cm"]) if last_assessment and last_assessment.get("altura_cm") else 170.0

    peso = st.number_input("Peso (kg)", min_value=1.0, step=0.1, value=peso_default)
    altura = st.number_input("Altura (cm)", min_value=50.0, step=0.5, value=altura_default)

fator = st.selectbox(
    "Fator de atividade",
    [("Sedentário (1.2)", 1.2), ("Leve (1.375)", 1.375), ("Moderado (1.55)", 1.55),
     ("Alto (1.725)", 1.725), ("Muito alto (1.9)", 1.9)],
    format_func=lambda x: x[0]
)[1]

bmr = mifflin_st_jeor(sexo, peso, altura, idade)
gasto = tdee(bmr, fator)

c1, c2, c3 = st.columns(3)
c1.metric("BMR", f"{bmr:.0f} kcal")
c2.metric("TDEE", f"{gasto:.0f} kcal")

meta = st.selectbox(
    "Meta calórica",
    ["Déficit (-15%)", "Déficit (-20%)", "Manutenção (0%)", "Superávit (+10%)", "Superávit (+15%)"]
)
ajuste = {
    "Déficit (-15%)": 0.85,
    "Déficit (-20%)": 0.80,
    "Manutenção (0%)": 1.00,
    "Superávit (+10%)": 1.10,
    "Superávit (+15%)": 1.15
}[meta]

calorias_alvo = gasto * ajuste
c3.metric("Calorias-alvo", f"{calorias_alvo:.0f} kcal/dia")

st.divider()
st.subheader("Macronutrientes")

p_gkg = st.slider("Proteína (g/kg)", 1.2, 2.6, 1.8, 0.1)
fat_pct = st.slider("Gordura (% das calorias)", 0.15, 0.40, 0.25, 0.01)

macros = macros_por_calorias(calorias_alvo, p_gkg, peso, fat_pct)
st.write(macros)

colA, colB = st.columns(2)

with colA:
    if st.button("Salvar dieta"):
        create_diet(
            pid,
            {
                "data_iso": date.today().isoformat(),
                "bmr": round(bmr, 1),
                "tdee": round(gasto, 1),
                "calorias_alvo": round(calorias_alvo, 1),
                "meta": meta,
                "p_gkg": float(p_gkg),
                "fat_pct": float(fat_pct),
                "proteina_g": float(macros["proteina_g"]),
                "carbo_g": float(macros["carbo_g"]),
                "gordura_g": float(macros["gordura_g"]),
            },
            user_id=uid
        )
        st.success("Dieta salva no banco.")

with colB:
    last_diet = get_last_diet(pid, user_id=uid)
    if last_diet:
        st.caption("Última dieta salva:")
        st.json(last_diet)

