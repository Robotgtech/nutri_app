def mifflin_st_jeor(sexo: str, peso: float, altura_cm: float, idade: int) -> float:
    # BMR
    base = 10 * peso + 6.25 * altura_cm - 5 * idade
    if sexo.lower().startswith("m"):
        return base + 5
    return base - 161

def tdee(bmr: float, fator_atividade: float) -> float:
    return bmr * fator_atividade

def macros_por_calorias(calorias: float, p_gkg: float, peso: float, fat_pct: float):
    # proteína em g/kg; gordura % das calorias; resto carbo
    proteina_g = p_gkg * peso
    prot_kcal = proteina_g * 4

    gordura_kcal = calorias * fat_pct
    gordura_g = gordura_kcal / 9

    carbo_kcal = max(calorias - prot_kcal - gordura_kcal, 0)
    carbo_g = carbo_kcal / 4

    return {
        "proteina_g": round(proteina_g, 1),
        "gordura_g": round(gordura_g, 1),
        "carbo_g": round(carbo_g, 1),
    }

def mifflin_st_jeor(sexo: str, peso: float, altura_cm: float, idade: int) -> float:
    base = 10 * peso + 6.25 * altura_cm - 5 * idade
    if sexo.lower().startswith("m"):
        return base + 5
    return base - 161

def tdee(bmr: float, fator_atividade: float) -> float:
    return bmr * fator_atividade

def macros_por_calorias(calorias: float, p_gkg: float, peso: float, fat_pct: float):
    proteina_g = p_gkg * peso
    prot_kcal = proteina_g * 4

    gordura_kcal = calorias * fat_pct
    gordura_g = gordura_kcal / 9

    carbo_kcal = max(calorias - prot_kcal - gordura_kcal, 0)
    carbo_g = carbo_kcal / 4

    return {
        "proteina_g": round(proteina_g, 1),
        "gordura_g": round(gordura_g, 1),
        "carbo_g": round(carbo_g, 1),
    }
