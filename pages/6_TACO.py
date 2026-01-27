import streamlit as st
import pandas as pd

from utils.bootstrap import bootstrap
from utils.db import upsert_foods, count_foods, search_foods, clear_foods

def parse_num(x):
    """
    Converte valores da TACO para número:
    - 'Tr' / 'tr' => 0.0
    - '-' / '' / None => None
    - '1,23' => 1.23
    """
    if x is None:
        return None

    s = str(x).strip()
    if s == "" or s == "-" or s.lower() in {"nan", "none"}:
        return None
    if s.lower() == "tr":
        return 0.0

    # troca vírgula por ponto (padrão BR)
    s = s.replace(",", ".")

    try:
        return float(s)
    except ValueError:
        return None

st.set_page_config(page_title="TACO - Alimentos", page_icon="🍎", layout="wide")
bootstrap(show_patient_picker=False, require_login=True)

from utils.feedback_widget import feedback_widget
feedback_widget("TACO")

st.title("🍎 Base de Alimentos (TACO)")

st.caption(f"Alimentos cadastrados no sistema: {count_foods()}")

st.divider()
st.subheader("1) Importar arquivo (CSV ou Excel)")

uploaded = st.file_uploader("Envie o arquivo da TACO", type=["csv", "xlsx", "xls"])

with st.expander("Opções de importação"):
    sheet_name = st.text_input("Nome da aba (se for Excel). Deixe vazio para primeira aba.", "")
    sep = st.text_input("Separador CSV (se precisar). Normalmente vírgula ',' ou ponto e vírgula ';'. Deixe vazio para auto.", "")

    st.markdown("**Mapeamento de colunas** (coloque os nomes EXATOS do seu arquivo):")
    col_nome = st.text_input("Coluna: Nome do alimento", "Alimento")
    col_kcal = st.text_input("Coluna: Energia (kcal)", "Energia (kcal)")
    col_p = st.text_input("Coluna: Proteína (g)", "Proteína (g)")
    col_c = st.text_input("Coluna: Carboidrato (g)", "Carboidrato (g)")
    col_g = st.text_input("Coluna: Gordura/Lipídeos (g)", "Lipídeos (g)")
    col_fib = st.text_input("Coluna: Fibra (g)", "Fibra alimentar (g)")
    col_na = st.text_input("Coluna: Sódio (mg)", "Sódio (mg)")

    base_g = st.number_input("Base dos nutrientes (g)", min_value=1.0, value=100.0, step=1.0)

colA, colB = st.columns(2)
with colA:
    reset = st.button("🧹 Limpar base de alimentos (zera foods)")
with colB:
    do_import = st.button("⬆️ Importar agora", type="primary", disabled=(uploaded is None))

if reset:
    clear_foods()
    st.success("Base foods limpa.")

df = None
if uploaded is not None:
    try:
        if uploaded.name.lower().endswith(".csv"):
            if sep.strip():
                df = pd.read_csv(uploaded, sep=sep.strip())
            else:
                df = pd.read_csv(uploaded, sep=None, engine="python")
        else:
            if sheet_name.strip():
                df = pd.read_excel(uploaded, sheet_name=sheet_name.strip())
            else:
                df = pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")

if df is not None:
    st.write("Prévia do arquivo:")
    st.dataframe(df.head(20), use_container_width=True)

if do_import and df is not None:
    # Normaliza colunas (remove espaços)
    df_cols = {c: str(c).strip() for c in df.columns}
    df = df.rename(columns=df_cols)

    missing = []
    for c in [col_nome, col_kcal, col_p, col_c, col_g, col_fib, col_na]:
        if c and c not in df.columns:
            missing.append(c)

    # Nome é obrigatório
    if col_nome not in df.columns:
        st.error(f"Coluna de nome não encontrada: '{col_nome}'. Ajuste no painel de opções.")
        st.stop()

    # Constrói linhas para inserir (as colunas opcionais podem faltar)
    def get_val(row, col):
        if col and col in row and pd.notna(row[col]):
            return row[col]
        return None

    rows = []
    for _, r in df.iterrows():
        nome = str(r[col_nome]).strip() if pd.notna(r[col_nome]) else ""
        if not nome:
            continue

        rows.append({
            "nome": nome,
            "base_g": float(base_g),
            "kcal": parse_num(get_val(r, col_kcal)),
            "proteina_g": parse_num(get_val(r, col_p)),
            "carbo_g": parse_num(get_val(r, col_c)),
            "gordura_g": parse_num(get_val(r, col_g)),
            "fibra_g": parse_num(get_val(r, col_fib)),
            "sodio_mg": parse_num(get_val(r, col_na)),
        })

    upsert_foods(rows)
    st.success(f"Importação concluída! Total foods agora: {count_foods()}")

st.divider()
st.subheader("2) Buscar alimento e calcular por gramas")

q = st.text_input("Buscar (ex: arroz, banana, frango)")
results = search_foods(q, limit=50) if q else []

if results:
    choice = st.selectbox("Resultados", results, format_func=lambda x: x["nome"])
    grams = st.number_input("Quantidade (g)", min_value=0.0, value=100.0, step=1.0)

    base = choice.get("base_g") or 100.0
    factor = grams / float(base) if base else 0.0

    kcal = (choice.get("kcal") or 0) * factor
    p = (choice.get("proteina_g") or 0) * factor
    c = (choice.get("carbo_g") or 0) * factor
    g = (choice.get("gordura_g") or 0) * factor
    fib = (choice.get("fibra_g") or 0) * factor
    na = (choice.get("sodio_mg") or 0) * factor

    col1, col2, col3 = st.columns(3)
    col1.metric("Kcal", f"{kcal:.1f}")
    col2.metric("Proteína (g)", f"{p:.1f}")
    col3.metric("Carbo (g)", f"{c:.1f}")

    col4, col5, col6 = st.columns(3)
    col4.metric("Gordura (g)", f"{g:.1f}")
    col5.metric("Fibra (g)", f"{fib:.1f}")
    col6.metric("Sódio (mg)", f"{na:.1f}")
elif q:
    st.info("Nenhum alimento encontrado.")
