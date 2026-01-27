import math
import streamlit as st
from datetime import date

from utils.bootstrap import bootstrap
from utils.db import get_patient, create_assessment, get_last_assessment, log_event

st.set_page_config(page_title="Avaliação", page_icon="📋", layout="wide")
bootstrap(show_patient_picker=True, require_login=True)

from utils.feedback_widget import feedback_widget
feedback_widget("Avaliação")

st.title("📋 Avaliação Nutricional")

# -----------------------------
# Helpers de cálculo
# -----------------------------
def calc_imc(peso_kg: float, altura_cm: float) -> float | None:
    if peso_kg <= 0 or altura_cm <= 0:
        return None
    h_m = altura_cm / 100.0
    return peso_kg / (h_m * h_m)

def classificar_imc(imc: float) -> str:
    # OMS para adultos (simplificado)
    if imc < 18.5:
        return "Baixo peso"
    if imc < 25:
        return "Eutrofia"
    if imc < 30:
        return "Sobrepeso"
    if imc < 35:
        return "Obesidade grau I"
    if imc < 40:
        return "Obesidade grau II"
    return "Obesidade grau III"

def cc_status(sexo: str, cintura_cm: float) -> tuple[float, str]:
    corte = 80.0 if sexo == "Feminino" else 94.0
    if cintura_cm <= 0:
        return (corte, "—")
    return (corte, "Acima do ponto de corte" if cintura_cm >= corte else "Abaixo do ponto de corte")

def rcq_status(sexo: str, cintura_cm: float, quadril_cm: float) -> tuple[float, float | None, str]:
    corte = 0.85 if sexo == "Feminino" else 1.00
    if cintura_cm <= 0 or quadril_cm <= 0:
        return (corte, None, "—")
    rcq = cintura_cm / quadril_cm
    status = "Acima do ponto de corte" if rcq >= corte else "Abaixo do ponto de corte"
    return (corte, rcq, status)

def gordura_us_navy(sexo: str, altura_cm: float, cintura_cm: float, pescoco_cm: float, quadril_cm: float | None) -> float | None:
    # Fórmula US Navy
    # Homem: 495 / (1.0324 - 0.19077*log10(cintura - pescoco) + 0.15456*log10(altura)) - 450
    # Mulher: 495 / (1.29579 - 0.35004*log10(cintura + quadril - pescoco) + 0.22100*log10(altura)) - 450
    if altura_cm <= 0 or cintura_cm <= 0 or pescoco_cm <= 0:
        return None

    try:
        if sexo == "Masculino":
            x = cintura_cm - pescoco_cm
            if x <= 0:
                return None
            bf = 495 / (1.0324 - 0.19077 * math.log10(x) + 0.15456 * math.log10(altura_cm)) - 450
            return bf
        else:
            if quadril_cm is None or quadril_cm <= 0:
                return None
            x = cintura_cm + quadril_cm - pescoco_cm
            if x <= 0:
                return None
            bf = 495 / (1.29579 - 0.35004 * math.log10(x) + 0.22100 * math.log10(altura_cm)) - 450
            return bf
    except ValueError:
        return None

# -----------------------------
# Carregar paciente
# -----------------------------
pid = st.session_state.patient_id
if not pid:
    st.warning("Selecione um paciente na barra lateral.")
    st.stop()

uid = st.session_state["user"]["id"]
patient = get_patient(pid, user_id=uid)

st.subheader(f"Paciente: {patient['nome']} (ID {patient['id']})")

last = get_last_assessment(pid, user_id=uid)

if last:
    st.caption("Última avaliação registrada:")
    st.json(last)

# -----------------------------
# Form
# -----------------------------
# --- sexo vindo do cadastro (FORA do form) ---
sexo_raw = (patient.get("sexo") or "").strip().lower()

if sexo_raw in ["m", "masc", "masculino", "homem"]:
    sexo = "Masculino"
elif sexo_raw in ["f", "fem", "feminino", "mulher"]:
    sexo = "Feminino"
else:
    st.warning(
        "⚠️ Sexo não informado no cadastro do paciente. "
        "Vá em Cadastro de Pacientes e preencha o sexo."
    )
    st.stop()

st.caption(f"Sexo do cadastro: **{sexo}**")

# --- form ---
with st.form("avaliacao"):
    col1, col2 = st.columns(2)

    with col1:
        peso = st.number_input(
            "Peso (kg)",
            min_value=0.0, step=0.1,
            value=float(last["peso"]) if last and last.get("peso") is not None else None,
            placeholder="Digite o peso"
        )
        altura_cm = st.number_input(
            "Altura (cm)",
            min_value=0.0, step=0.5,
            value=float(last["altura_cm"]) if last and last.get("altura_cm") is not None else None,
            placeholder="Digite a altura"
        )
        pescoco_cm = st.number_input(
            "Pescoço (cm) — US Navy",
            min_value=0.0, step=0.5,
            value=float(last["pescoco_cm"]) if last and last.get("pescoco_cm") is not None else None,
            placeholder="Digite o pescoço"
        )

    with col2:
        cintura_cm = st.number_input(
            "Cintura (cm)",
            min_value=0.0, step=0.5,
            value=float(last["cintura_cm"]) if last and last.get("cintura_cm") is not None else None,
            placeholder="Digite a cintura"
        )
        quadril_cm = st.number_input(
            "Quadril (cm)",
            min_value=0.0, step=0.5,
            value=float(last["quadril_cm"]) if last and last.get("quadril_cm") is not None else None,
            placeholder="Digite o quadril"
        )

    objetivo = st.selectbox("Objetivo", ["Emagrecimento", "Ganho de massa", "Manutenção", "Performance/saúde"])
    atividade = st.selectbox("Nível de atividade", ["Sedentário", "Leve", "Moderado", "Alto", "Muito alto"])
    sono_h = st.number_input(
        "Sono (h/dia)",
        min_value=0.0, max_value=24.0, step=0.5,
        value=float(last["sono_h"]) if last and last.get("sono_h") is not None else None,
        placeholder="Horas de sono"
    )
    obs = st.text_area("Observações", value=(last.get("obs", "") if last else ""))

    # ✅ ESTE BOTÃO PRECISA ESTAR AQUI DENTRO (mesma indentação de 'obs')
    ok = st.form_submit_button("Salvar avaliação")


# Preview dos cálculos dentro do form (antes de salvar)
st.markdown("### Resultados (prévia)")

# ---------- IMC ----------
imc = None
if peso is not None and altura_cm is not None:
    imc = calc_imc(float(peso), float(altura_cm))

if imc is not None:
    st.write(f"**IMC:** {imc:.2f} — **{classificar_imc(imc)}**")
else:
    st.write("**IMC:** —")

# ---------- Cintura (CC) ----------
corte_cc = 80.0 if sexo == "Feminino" else 94.0
if cintura_cm is not None and float(cintura_cm) > 0:
    _, status_cc = cc_status(sexo, float(cintura_cm))
    st.write(f"**Cintura (CC):** {float(cintura_cm):.1f} cm — corte **{corte_cc:.0f} cm** → **{status_cc}**")
else:
    st.write(f"**Cintura (CC):** — (corte {corte_cc:.0f} cm)")

# ---------- RCQ ----------
corte_rcq = 0.85 if sexo == "Feminino" else 1.00
rcq = None
status_rcq = "—"
if cintura_cm is not None and quadril_cm is not None and float(cintura_cm) > 0 and float(quadril_cm) > 0:
    _, rcq, status_rcq = rcq_status(sexo, float(cintura_cm), float(quadril_cm))

if rcq is not None:
    st.write(f"**RCQ:** {rcq:.2f} — corte **{corte_rcq:.2f}** → **{status_rcq}**")
else:
    st.write(f"**RCQ:** — (corte {corte_rcq:.2f})")

# ---------- % Gordura (US Navy) ----------
bf = None
if altura_cm is not None and cintura_cm is not None and pescoco_cm is not None:
    # Regras mínimas: altura, cintura e pescoço
    if float(altura_cm) > 0 and float(cintura_cm) > 0 and float(pescoco_cm) > 0:
        quad_for_navy = None
        if sexo == "Feminino":
            if quadril_cm is not None and float(quadril_cm) > 0:
                quad_for_navy = float(quadril_cm)
            else:
                quad_for_navy = None  # sem quadril não calcula em mulher

        bf = gordura_us_navy(
            sexo=sexo,
            altura_cm=float(altura_cm),
            cintura_cm=float(cintura_cm),
            pescoco_cm=float(pescoco_cm),
            quadril_cm=quad_for_navy
        )

if bf is not None:
    st.write(f"**% Gordura (US Navy):** {bf:.1f}%")
else:
    if sexo == "Feminino":
        st.write("**% Gordura (US Navy):** — (preencha pescoço + cintura + altura + quadril)")
    else:
        st.write("**% Gordura (US Navy):** — (preencha pescoço + cintura + altura)")

ok = st.form_submit_button("Salvar avaliação")


# -----------------------------
# Salvar
# -----------------------------
if ok:
    try:
        assessment_id = create_assessment(
            pid,
            {
                "data_iso": date.today().isoformat(),
                "peso": float(peso),
                "altura_cm": float(altura_cm),
                "cintura_cm": float(cintura_cm),
                "quadril_cm": float(quadril_cm),
                "pescoco_cm": float(pescoco_cm),
                "bf_usnavy_pct": float(bf) if bf is not None else None,
                "objetivo": objetivo,
                "atividade": atividade,
                "sono_h": float(sono_h),
                "obs": obs.strip(),
            },
            user_id=uid
        )

        log_event(
            user_id=uid,
            event_name="assessment_created",
            meta={"patient_id": pid, "assessment_id": assessment_id},
        )

        st.success("Avaliação salva com sucesso!")
        st.rerun()

    except Exception as e:
        log_event(
            user_id=uid,
            event_name="error",
            meta={
                "page": "Avaliação Nutricional",
                "action": "create_assessment",
                "error": str(e),
            },
        )
        st.error("Erro ao salvar avaliação. Já registrei para correção.")

