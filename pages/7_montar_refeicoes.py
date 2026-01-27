import streamlit as st
from utils.bootstrap import bootstrap
from utils.db import (
    get_patient, get_last_diet, log_event,
    search_foods, add_diet_item, list_diet_items, delete_diet_item
)

st.set_page_config(page_title="Montar Refeições", page_icon="🍽️", layout="wide")
bootstrap(show_patient_picker=True, require_login=True)

from utils.feedback_widget import feedback_widget
feedback_widget("Montar refeições")

st.title("🍽️ Montar Refeições")

uid = st.session_state["user"]["id"]
pid = st.session_state.patient_id
if not pid:
    st.warning("Selecione um paciente na barra lateral.")
    st.stop()

patient = get_patient(pid, user_id=uid)
if not patient:
    st.error("Paciente não encontrado (ou você não tem acesso).")
    st.stop()

diet = get_last_diet(pid, user_id=uid)
diet_id = diet["id"] if diet else None

st.subheader(f"Paciente: {patient['nome']} (ID {patient['id']})")
if diet:
    st.caption(f"Dieta ativa (última salva): {diet.get('calorias_alvo', '')} kcal | P {diet.get('proteina_g','')}g C {diet.get('carbo_g','')}g G {diet.get('gordura_g','')}g")
else:
    st.warning("Ainda não há dieta salva para este paciente. Você pode montar refeições mesmo assim, mas recomendo salvar uma dieta primeiro.")

st.divider()

# -------- Adicionar item --------
st.subheader("Adicionar alimento na refeição")

meal = st.selectbox("Refeição", ["Café da manhã", "Lanche manhã", "Almoço", "Lanche tarde", "Jantar", "Ceia"])

q = st.text_input("Buscar alimento (TACO)", placeholder="ex: arroz, banana, frango")
results = search_foods(q, limit=50) if q else []

if results:
    food = st.selectbox("Escolha o alimento", results, format_func=lambda x: x["nome"])
    grams = st.number_input("Quantidade (g)", min_value=0.0, value=100.0, step=1.0)

    base = food.get("base_g") or 100.0
    factor = grams / float(base) if base else 0.0

    kcal = (food.get("kcal") or 0) * factor
    p = (food.get("proteina_g") or 0) * factor
    c = (food.get("carbo_g") or 0) * factor
    g = (food.get("gordura_g") or 0) * factor

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Kcal", f"{kcal:.1f}")
    col2.metric("P (g)", f"{p:.1f}")
    col3.metric("C (g)", f"{c:.1f}")
    col4.metric("G (g)", f"{g:.1f}")

    if st.button("➕ Adicionar à refeição", type="primary"):
        try:
            item_id = add_diet_item(
                user_id=uid,
                patient_id=pid,
                diet_id=diet_id,
                meal=meal,
                food_id=food["id"],
                grams=float(grams),
            )

            log_event(
                user_id=uid,
                event_name="diet_item_added",
                meta={
                    "diet_id": diet_id,
                    "item_id": item_id,
                    "food_id": food["id"],
                    "grams": float(grams)
                }
            )

            st.success("Item adicionado!")
            st.rerun()

        except Exception as e:
            log_event(
                user_id=uid,
                event_name="error",
                meta={
                    "page": "Montar refeições",
                    "action": "add_diet_item",
                    "error": str(e)
                }
            )
            st.error("Erro ao adicionar item à refeição.")

elif q:
    st.info("Nenhum alimento encontrado para essa busca.")

st.divider()

# -------- Listagem + totais --------
st.subheader("Itens do plano alimentar")

items = list_diet_items(uid, pid, diet_id=diet_id)

if not items:
    st.caption("Nenhum item adicionado ainda.")
    st.stop()

def item_macros(it):
    base = it.get("base_g") or 100.0
    grams = it.get("grams") or 0.0
    factor = grams / float(base) if base else 0.0
    return {
        "kcal": (it.get("kcal") or 0) * factor,
        "p": (it.get("proteina_g") or 0) * factor,
        "c": (it.get("carbo_g") or 0) * factor,
        "g": (it.get("gordura_g") or 0) * factor,
    }

# totais por refeição e dia
tot_day = {"kcal": 0, "p": 0, "c": 0, "g": 0}
by_meal = {}

for it in items:
    m = it["meal"]
    mm = item_macros(it)
    by_meal.setdefault(m, {"kcal": 0, "p": 0, "c": 0, "g": 0})
    for k in tot_day:
        tot_day[k] += mm[k]
        by_meal[m][k] += mm[k]

# cards do total do dia
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total do dia (kcal)", f"{tot_day['kcal']:.0f}")
c2.metric("Proteína (g)", f"{tot_day['p']:.1f}")
c3.metric("Carbo (g)", f"{tot_day['c']:.1f}")
c4.metric("Gordura (g)", f"{tot_day['g']:.1f}")

# comparação com meta (se tiver dieta)
if diet and diet.get("calorias_alvo"):
    st.caption("Comparação com meta (última dieta salva):")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Meta kcal", f"{float(diet.get('calorias_alvo')):.0f}", delta=f"{tot_day['kcal'] - float(diet.get('calorias_alvo')):+.0f}")
    d2.metric("Meta P", f"{float(diet.get('proteina_g') or 0):.1f}", delta=f"{tot_day['p'] - float(diet.get('proteina_g') or 0):+.1f}")
    d3.metric("Meta C", f"{float(diet.get('carbo_g') or 0):.1f}", delta=f"{tot_day['c'] - float(diet.get('carbo_g') or 0):+.1f}")
    d4.metric("Meta G", f"{float(diet.get('gordura_g') or 0):.1f}", delta=f"{tot_day['g'] - float(diet.get('gordura_g') or 0):+.1f}")

st.divider()

# tabela por refeição + botão deletar item
for meal_name, totals in by_meal.items():
    st.markdown(f"### {meal_name}  —  {totals['kcal']:.0f} kcal | P {totals['p']:.1f} | C {totals['c']:.1f} | G {totals['g']:.1f}")

    meal_items = [it for it in items if it["meal"] == meal_name]
    for it in meal_items:
        mm = item_macros(it)
        cols = st.columns([6, 2, 2, 2, 2, 2])
        cols[0].write(f"• **{it['nome']}**")
        cols[1].write(f"{it['grams']:.0f} g")
        cols[2].write(f"{mm['kcal']:.0f} kcal")
        cols[3].write(f"P {mm['p']:.1f}")
        cols[4].write(f"C {mm['c']:.1f}")
        if cols[5].button("🗑️", key=f"del_{it['id']}"):
            try:
                delete_diet_item(uid, it["id"])

                log_event(
                    user_id=uid,
                    event_name="diet_item_deleted",
                    meta={"item_id": it["id"]}
                )

                st.rerun()

            except Exception as e:
                log_event(
                    user_id=uid,
                    event_name="error",
                    meta={
                        "page": "Montar refeições",
                        "action": "delete_diet_item",
                        "error": str(e)
                    }
                )
                st.error("Erro ao remover item.")

