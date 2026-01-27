from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import datetime

def build_pdf(path, patient: dict, assessment: dict | None, diet: dict | None, diet_items: list[dict] | None = None):
    diet_items = diet_items or []
    
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4

    x = 2 * cm
    y = height - 2 * cm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, "RELATÓRIO NUTRICIONAL")
    y -= 0.8 * cm

    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 1.0 * cm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Dados do paciente")
    y -= 0.6 * cm

    c.setFont("Helvetica", 11)
    lines = [
        f"ID: {patient.get('id')}",
        f"Nome: {patient.get('nome','')}",
        f"Telefone: {patient.get('telefone','')}",
        f"E-mail: {patient.get('email','')}",
        f"Nascimento: {patient.get('nascimento','')}",
        f"Sexo: {patient.get('sexo','')}",
    ]
    for line in lines:
        c.drawString(x, y, line)
        y -= 0.55 * cm

    y -= 0.4 * cm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Última avaliação")
    y -= 0.6 * cm

    c.setFont("Helvetica", 11)
    if assessment:
        a_lines = [
            f"Data: {assessment.get('data_iso','')}",
            f"Peso: {assessment.get('peso','')} kg | Altura: {assessment.get('altura_cm','')} cm",
            f"Cintura: {assessment.get('cintura_cm','')} cm | Quadril: {assessment.get('quadril_cm','')} cm",
            f"Objetivo: {assessment.get('objetivo','')} | Atividade: {assessment.get('atividade','')}",
            f"Sono: {assessment.get('sono_h','')} h/dia",
        ]
        for line in a_lines:
            c.drawString(x, y, line)
            y -= 0.55 * cm

        obs = (assessment.get("obs") or "").strip()
        if obs:
            y -= 0.2 * cm
            c.setFont("Helvetica-Oblique", 10)
            c.drawString(x, y, f"Obs: {obs[:120]}")
            c.setFont("Helvetica", 11)
            y -= 0.6 * cm
    else:
        c.drawString(x, y, "Sem avaliação registrada.")
        y -= 0.55 * cm

    y -= 0.4 * cm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Plano dietético (estimativa)")
    y -= 0.6 * cm

    c.setFont("Helvetica", 11)
    if diet:
        d_lines = [
            f"Data: {diet.get('data_iso','')} | Meta: {diet.get('meta','')}",
            f"Calorias-alvo: {diet.get('calorias_alvo','')} kcal/dia",
            f"Proteína: {diet.get('proteina_g','')} g | Carbo: {diet.get('carbo_g','')} g | Gordura: {diet.get('gordura_g','')} g",
            f"BMR: {diet.get('bmr','')} | TDEE: {diet.get('tdee','')}",
        ]
        for line in d_lines:
            c.drawString(x, y, line)
            y -= 0.55 * cm
    else:
        c.drawString(x, y, "Sem dieta registrada.")
        y -= 0.55 * cm

    # -------------------------------
    # Plano alimentar (refeições)
    # -------------------------------

    def item_macros(it):
        base = it.get("base_g") or 100.0
        grams = it.get("grams") or 0.0
        factor = (float(grams) / float(base)) if base else 0.0
        return {
            "kcal": (it.get("kcal") or 0) * factor,
            "p": (it.get("proteina_g") or 0) * factor,
            "c": (it.get("carbo_g") or 0) * factor,
            "g": (it.get("gordura_g") or 0) * factor,
        }

    if diet_items:
        y -= 0.6 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "Plano alimentar")
        y -= 0.6 * cm

        c.setFont("Helvetica", 10)

        current_meal = None
        tot_day = {"kcal": 0, "p": 0, "c": 0, "g": 0}

        for it in diet_items:
            meal = it.get("meal", "Refeição")

            # Quebra de página
            if y < 3 * cm:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - 2 * cm

            if meal != current_meal:
                current_meal = meal
                y -= 0.4 * cm
                c.setFont("Helvetica-Bold", 11)
                c.drawString(x, y, meal)
                y -= 0.4 * cm
                c.setFont("Helvetica", 10)

            mm = item_macros(it)
            tot_day["kcal"] += mm["kcal"]
            tot_day["p"] += mm["p"]
            tot_day["c"] += mm["c"]
            tot_day["g"] += mm["g"]

            line = (
                f"- {it.get('nome','')} | {float(it.get('grams') or 0):.0f} g | "
                f"{mm['kcal']:.0f} kcal | "
                f"P {mm['p']:.1f} g | C {mm['c']:.1f} g | G {mm['g']:.1f} g"
            )
            c.drawString(x, y, line)
            y -= 0.45 * cm

        y -= 0.6 * cm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(
            x,
            y,
            f"Total do dia: {tot_day['kcal']:.0f} kcal | "
            f"P {tot_day['p']:.1f} g | C {tot_day['c']:.1f} g | G {tot_day['g']:.1f} g"
        )


    c.showPage()
    c.save()
