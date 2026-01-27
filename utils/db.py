import os
import streamlit as st
import sqlite3
import json
from pathlib import Path
from datetime import datetime

SQLITE_PATH = Path("data") / "nutriapp.db"

def normalize_db_url(url: str) -> str:
    # Alguns provedores dão "postgres://"
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url

RAW_DATABASE_URL = os.getenv("DATABASE_URL")  # só deve existir em produção (Postgres)
USE_POSTGRES = bool(RAW_DATABASE_URL)

DATABASE_URL = normalize_db_url(RAW_DATABASE_URL) if RAW_DATABASE_URL else None

def get_conn():
    if USE_POSTGRES:
        return get_postgres_conn()
    else:
        return get_sqlite_conn()

def get_sqlite_conn():
    SQLITE_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def get_postgres_conn():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        cursor_factory=RealDictCursor,
    )

# --------------------------------------------------
# Inicialização do banco
# --------------------------------------------------

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    if USE_POSTGRES:
        auto_id = "SERIAL PRIMARY KEY"
        text = "TEXT"
        real = "REAL"
    else:
        auto_id = "INTEGER PRIMARY KEY AUTOINCREMENT"
        text = "TEXT"
        real = "REAL"

    # ---------- users (futuro login) ----------
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS users (
        id {auto_id},
        email {text} UNIQUE,
        password_hash {text},
        created_at {text}
    );
    """)

    # ---------- patients ----------
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS patients (
        id {auto_id},
        user_id INTEGER,
        nome {text} NOT NULL,
        telefone {text},
        email {text},
        nascimento {text},
        sexo {text},
        obs {text}
    );
    """)

    # ---------- appointments ----------
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS appointments (
        id {auto_id},
        user_id INTEGER,
        patient_id INTEGER NOT NULL,
        dt_iso {text} NOT NULL,
        tipo {text},
        notas {text}
    );
    """)

    # ---------- assessments ----------
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS assessments (
        id {auto_id},
        user_id INTEGER,
        patient_id INTEGER NOT NULL,
        data_iso {text} NOT NULL,
        peso {real},
        altura_cm {real},
        cintura_cm {real},
        quadril_cm {real},
        objetivo {text},
        atividade {text},
        sono_h {real},
        obs {text}
    );
    """)

    # ---------- diets ----------
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS diets (
        id {auto_id},
        user_id INTEGER,
        patient_id INTEGER NOT NULL,
        data_iso {text} NOT NULL,
        bmr {real},
        tdee {real},
        calorias_alvo {real},
        meta {text},
        p_gkg {real},
        fat_pct {real},
        proteina_g {real},
        carbo_g {real},
        gordura_g {real}
    );
    """)

    # ---------- foods (TACO) ----------
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS foods (
        id {auto_id},
        nome {text} NOT NULL,
        base_g {real} DEFAULT 100,
        kcal {real},
        proteina_g {real},
        carbo_g {real},
        gordura_g {real},
        fibra_g {real},
        sodio_mg {real}
    );
    """)

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS diet_items (
            id {auto_id},
            user_id INTEGER,
            patient_id INTEGER NOT NULL,
            diet_id INTEGER,
            meal {text} NOT NULL,
            food_id INTEGER NOT NULL,
            grams {real} NOT NULL,
            created_at {text}
        );
        """)
    
    # ---------- beta_allowlist (beta fechada) ----------
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS beta_allowlist (
            id {auto_id},
            email {text} UNIQUE NOT NULL,
            created_at {text}
        );
        """)
    
    # ---------- feedback ----------
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS feedback (
            id {auto_id},
            user_id INTEGER,
            page {text},
            message {text} NOT NULL,
            rating INTEGER,
            created_at {text}
        );
        """)

    # ---------- event_logs ----------
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS event_logs (
            id {auto_id},
            user_id INTEGER,
            event_name {text} NOT NULL,
            meta {text},
            created_at {text}
        );
        """)

    conn.commit()
    conn.close()

# --------------------------------------------------
# Helpers internos
# --------------------------------------------------

def _now():
    return datetime.utcnow().isoformat()

def _dicts(rows):
    # sqlite: sqlite3.Row -> dict ok
    # postgres (RealDictCursor): já vem dict
    return [dict(r) for r in rows]

def is_email_allowed(email: str) -> bool:
    email = (email or "").strip().lower()
    if not email:
        return False

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT 1 FROM beta_allowlist WHERE email = ? LIMIT 1"
        if not USE_POSTGRES else
        "SELECT 1 FROM beta_allowlist WHERE email = %s LIMIT 1",
        (email,)
    )

    row = cur.fetchone()
    conn.close()
    return bool(row)

def add_allowed_email(email: str):
    email = (email or "").strip().lower()
    if not email:
        return

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO beta_allowlist (email, created_at) VALUES (?, ?)"
        if not USE_POSTGRES else
        "INSERT INTO beta_allowlist (email, created_at) VALUES (%s, %s) ON CONFLICT (email) DO NOTHING",
        (email, _now())
    )

    conn.commit()
    conn.close()


# --------------------------------------------------
# Patients
# --------------------------------------------------

def create_patient(nome, telefone="", email="", nascimento="", sexo="", obs="", user_id=None):
    conn = get_conn()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO patients (user_id, nome, telefone, email, nascimento, sexo, obs)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, nome, telefone, email, nascimento, sexo, obs))
        pid = cur.fetchone()["id"]
    else:
        cur.execute("""
            INSERT INTO patients (user_id, nome, telefone, email, nascimento, sexo, obs)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, nome, telefone, email, nascimento, sexo, obs))
        pid = cur.lastrowid

    conn.commit()
    conn.close()
    return pid

def list_patients(user_id=None):
    conn = get_conn()
    cur = conn.cursor()

    if user_id:
        cur.execute(
            "SELECT * FROM patients WHERE user_id = ? ORDER BY nome"
            if not USE_POSTGRES else
            "SELECT * FROM patients WHERE user_id = %s ORDER BY nome",
            (user_id,)
        )
    else:
        cur.execute("SELECT * FROM patients ORDER BY nome")

    rows = cur.fetchall()
    conn.close()
    return _dicts(rows)

def get_patient(patient_id, user_id=None):
    conn = get_conn()
    cur = conn.cursor()

    if user_id is not None:
        cur.execute(
            "SELECT * FROM patients WHERE id = ? AND user_id = ?"
            if not USE_POSTGRES else
            "SELECT * FROM patients WHERE id = %s AND user_id = %s",
            (patient_id, user_id)
        )
    else:
        cur.execute(
            "SELECT * FROM patients WHERE id = ?"
            if not USE_POSTGRES else
            "SELECT * FROM patients WHERE id = %s",
            (patient_id,)
        )

    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

# --------------------------------------------------
# Assessments
# --------------------------------------------------

def create_assessment(patient_id, payload: dict, user_id=None):
    conn = get_conn()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO assessments (
                user_id, patient_id, data_iso, peso, altura_cm, cintura_cm,
                quadril_cm, objetivo, atividade, sono_h, obs
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id,
            patient_id,
            payload.get("data_iso"),
            payload.get("peso"),
            payload.get("altura_cm"),
            payload.get("cintura_cm"),
            payload.get("quadril_cm"),
            payload.get("objetivo"),
            payload.get("atividade"),
            payload.get("sono_h"),
            payload.get("obs"),
        ))
        new_id = cur.fetchone()["id"]
    else:
        cur.execute("""
            INSERT INTO assessments (
                user_id, patient_id, data_iso, peso, altura_cm, cintura_cm,
                quadril_cm, objetivo, atividade, sono_h, obs
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            patient_id,
            payload.get("data_iso"),
            payload.get("peso"),
            payload.get("altura_cm"),
            payload.get("cintura_cm"),
            payload.get("quadril_cm"),
            payload.get("objetivo"),
            payload.get("atividade"),
            payload.get("sono_h"),
            payload.get("obs"),
        ))
        new_id = cur.lastrowid

    conn.commit()
    conn.close()
    return new_id


def get_last_assessment(patient_id, user_id=None):
    conn = get_conn()
    cur = conn.cursor()

    if user_id is not None:
        cur.execute("""
            SELECT * FROM assessments
            WHERE patient_id = ? AND user_id = ?
            ORDER BY data_iso DESC, id DESC
            LIMIT 1
        """ if not USE_POSTGRES else """
            SELECT * FROM assessments
            WHERE patient_id = %s AND user_id = %s
            ORDER BY data_iso DESC, id DESC
            LIMIT 1
        """, (patient_id, user_id))
    else:
        cur.execute("""
            SELECT * FROM assessments
            WHERE patient_id = ?
            ORDER BY data_iso DESC, id DESC
            LIMIT 1
        """ if not USE_POSTGRES else """
            SELECT * FROM assessments
            WHERE patient_id = %s
            ORDER BY data_iso DESC, id DESC
            LIMIT 1
        """, (patient_id,))

    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

# --------------------------------------------------
# Diets
# --------------------------------------------------

def create_diet(patient_id, payload: dict, user_id=None):
    conn = get_conn()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO diets (
                user_id, patient_id, data_iso, bmr, tdee, calorias_alvo,
                meta, p_gkg, fat_pct, proteina_g, carbo_g, gordura_g
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id,
            patient_id,
            payload.get("data_iso"),
            payload.get("bmr"),
            payload.get("tdee"),
            payload.get("calorias_alvo"),
            payload.get("meta"),
            payload.get("p_gkg"),
            payload.get("fat_pct"),
            payload.get("proteina_g"),
            payload.get("carbo_g"),
            payload.get("gordura_g"),
        ))
        new_id = cur.fetchone()["id"]
    else:
        cur.execute("""
            INSERT INTO diets (
                user_id, patient_id, data_iso, bmr, tdee, calorias_alvo,
                meta, p_gkg, fat_pct, proteina_g, carbo_g, gordura_g
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            patient_id,
            payload.get("data_iso"),
            payload.get("bmr"),
            payload.get("tdee"),
            payload.get("calorias_alvo"),
            payload.get("meta"),
            payload.get("p_gkg"),
            payload.get("fat_pct"),
            payload.get("proteina_g"),
            payload.get("carbo_g"),
            payload.get("gordura_g"),
        ))
        new_id = cur.lastrowid

    conn.commit()
    conn.close()
    return new_id

def get_last_diet(patient_id, user_id=None):
    conn = get_conn()
    cur = conn.cursor()

    if user_id is not None:
        cur.execute("""
            SELECT * FROM diets
            WHERE patient_id = ? AND user_id = ?
            ORDER BY data_iso DESC, id DESC
            LIMIT 1
        """ if not USE_POSTGRES else """
            SELECT * FROM diets
            WHERE patient_id = %s AND user_id = %s
            ORDER BY data_iso DESC, id DESC
            LIMIT 1
        """, (patient_id, user_id))
    else:
        cur.execute("""
            SELECT * FROM diets
            WHERE patient_id = ?
            ORDER BY data_iso DESC, id DESC
            LIMIT 1
        """ if not USE_POSTGRES else """
            SELECT * FROM diets
            WHERE patient_id = %s
            ORDER BY data_iso DESC, id DESC
            LIMIT 1
        """, (patient_id,))

    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_email(email: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE email = ?"
        if not USE_POSTGRES else
        "SELECT * FROM users WHERE email = %s",
        (email.strip().lower(),)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(email: str, password_hash: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)"
        if not USE_POSTGRES else
        "INSERT INTO users (email, password_hash, created_at) VALUES (%s, %s, %s) RETURNING id",
        (email.strip().lower(), password_hash, _now())
    )

    user_id = None
    if USE_POSTGRES:
        user_id = cur.fetchone()[0]
    else:
        user_id = cur.lastrowid

    conn.commit()
    conn.close()
    return user_id

# --------------------------------------------------
# Appointments (Agenda)
# --------------------------------------------------

def create_appointment(patient_id, dt_iso, tipo="", notas="", user_id=None):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO appointments (
            user_id, patient_id, dt_iso, tipo, notas
        ) VALUES (?, ?, ?, ?, ?)
    """ if not USE_POSTGRES else """
        INSERT INTO appointments (
            user_id, patient_id, dt_iso, tipo, notas
        ) VALUES (%s, %s, %s, %s, %s)
    """, (
        user_id,
        patient_id,
        dt_iso,
        tipo,
        notas,
    ))

    conn.commit()
    conn.close()

def list_appointments(user_id=None):
    conn = get_conn()
    cur = conn.cursor()

    if user_id:
        cur.execute("""
            SELECT a.*, p.nome AS patient_nome
            FROM appointments a
            JOIN patients p ON p.id = a.patient_id
            WHERE a.user_id = ?
            ORDER BY a.dt_iso
        """ if not USE_POSTGRES else """
            SELECT a.*, p.nome AS patient_nome
            FROM appointments a
            JOIN patients p ON p.id = a.patient_id
            WHERE a.user_id = %s
            ORDER BY a.dt_iso
        """, (user_id,))
    else:
        cur.execute("""
            SELECT a.*, p.nome AS patient_nome
            FROM appointments a
            JOIN patients p ON p.id = a.patient_id
            ORDER BY a.dt_iso
        """)

    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --------------------------------------------------
# Foods (TACO)
# --------------------------------------------------

def upsert_foods(rows: list[dict]):
    """
    Insere alimentos. Se quiser impedir duplicados por nome, a gente melhora depois com UNIQUE + upsert.
    rows: [{"nome": ..., "kcal": ..., "proteina_g": ...}, ...]
    """
    conn = get_conn()
    cur = conn.cursor()

    for r in rows:
        nome = (r.get("nome") or "").strip()
        if not nome:
            continue

        params = (
            nome,
            r.get("base_g", 100.0),
            r.get("kcal"),
            r.get("proteina_g"),
            r.get("carbo_g"),
            r.get("gordura_g"),
            r.get("fibra_g"),
            r.get("sodio_mg"),
        )

        cur.execute("""
            INSERT INTO foods (nome, base_g, kcal, proteina_g, carbo_g, gordura_g, fibra_g, sodio_mg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """ if not USE_POSTGRES else """
            INSERT INTO foods (nome, base_g, kcal, proteina_g, carbo_g, gordura_g, fibra_g, sodio_mg)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, params)

    conn.commit()
    conn.close()

def count_foods():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM foods")
    n = cur.fetchone()[0]
    conn.close()
    return int(n)

def search_foods(query: str, limit: int = 50):
    q = (query or "").strip()
    if not q:
        return []
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM foods WHERE nome LIKE ? ORDER BY nome LIMIT ?"
        if not USE_POSTGRES else
        "SELECT * FROM foods WHERE nome ILIKE %s ORDER BY nome LIMIT %s",
        (f"%{q}%", limit)
    )

    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_food(food_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM foods WHERE id = ?"
        if not USE_POSTGRES else
        "SELECT * FROM foods WHERE id = %s",
        (food_id,)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def clear_foods():
    """Usado caso você queira reimportar do zero."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM foods")
    conn.commit()
    conn.close()

# --------------------------------------------------
# Diet Items (Montagem de refeições)
# --------------------------------------------------

def add_diet_item(user_id, patient_id, diet_id, meal, food_id, grams):
    conn = get_conn()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO diet_items (user_id, patient_id, diet_id, meal, food_id, grams, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, patient_id, diet_id, meal, food_id, grams, _now()))
        new_id = cur.fetchone()["id"]
    else:
        cur.execute("""
            INSERT INTO diet_items (user_id, patient_id, diet_id, meal, food_id, grams, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, patient_id, diet_id, meal, food_id, grams, _now()))
        new_id = cur.lastrowid

    conn.commit()
    conn.close()
    return new_id

def list_diet_items(user_id, patient_id, diet_id=None):
    conn = get_conn()
    cur = conn.cursor()

    if diet_id:
        cur.execute("""
            SELECT di.id, di.meal, di.grams, di.food_id,
                   f.nome, f.base_g, f.kcal, f.proteina_g, f.carbo_g, f.gordura_g, f.fibra_g, f.sodio_mg
            FROM diet_items di
            JOIN foods f ON f.id = di.food_id
            WHERE di.user_id = ? AND di.patient_id = ? AND di.diet_id = ?
            ORDER BY di.meal, di.id
        """ if not USE_POSTGRES else """
            SELECT di.id, di.meal, di.grams, di.food_id,
                   f.nome, f.base_g, f.kcal, f.proteina_g, f.carbo_g, f.gordura_g, f.fibra_g, f.sodio_mg
            FROM diet_items di
            JOIN foods f ON f.id = di.food_id
            WHERE di.user_id = %s AND di.patient_id = %s AND di.diet_id = %s
            ORDER BY di.meal, di.id
        """, (user_id, patient_id, diet_id))
    else:
        cur.execute("""
            SELECT di.id, di.meal, di.grams, di.food_id,
                   f.nome, f.base_g, f.kcal, f.proteina_g, f.carbo_g, f.gordura_g, f.fibra_g, f.sodio_mg
            FROM diet_items di
            JOIN foods f ON f.id = di.food_id
            WHERE di.user_id = ? AND di.patient_id = ?
            ORDER BY di.meal, di.id
        """ if not USE_POSTGRES else """
            SELECT di.id, di.meal, di.grams, di.food_id,
                   f.nome, f.base_g, f.kcal, f.proteina_g, f.carbo_g, f.gordura_g, f.fibra_g, f.sodio_mg
            FROM diet_items di
            JOIN foods f ON f.id = di.food_id
            WHERE di.user_id = %s AND di.patient_id = %s
            ORDER BY di.meal, di.id
        """, (user_id, patient_id))

    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_diet_item(user_id, item_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM diet_items WHERE id = ? AND user_id = ?"
        if not USE_POSTGRES else
        "DELETE FROM diet_items WHERE id = %s AND user_id = %s",
        (item_id, user_id)
    )
    conn.commit()
    conn.close()


def update_patient(patient_id, user_id, nome, telefone="", email="", nascimento=None, sexo="", obs=""):
        conn = get_conn()
        cur = conn.cursor()

        nasc_str = str(nascimento) if nascimento is not None else ""

        cur.execute("""
            UPDATE patients
            SET nome = ?, telefone = ?, email = ?, nascimento = ?, sexo = ?, obs = ?
            WHERE id = ? AND user_id = ?
        """ if not USE_POSTGRES else """
            UPDATE patients
            SET nome = %s, telefone = %s, email = %s, nascimento = %s, sexo = %s, obs = %s
            WHERE id = %s AND user_id = %s
        """, (nome, telefone, email, nasc_str, sexo, obs, patient_id, user_id))

        conn.commit()
        conn.close()    

def create_feedback(user_id: int, page: str, message: str, rating: int | None = None):
    page = (page or "").strip()
    message = (message or "").strip()
    if not message:
        return

    conn = get_conn()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO feedback (user_id, page, message, rating, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, page, message, rating, _now()))
    else:
        cur.execute("""
            INSERT INTO feedback (user_id, page, message, rating, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, page, message, rating, _now()))

    conn.commit()
    conn.close()


def list_feedback(limit: int = 200):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM feedback ORDER BY created_at DESC LIMIT ?"
        if not USE_POSTGRES else
        "SELECT * FROM feedback ORDER BY created_at DESC LIMIT %s",
        (limit,)
    )

    rows = cur.fetchall()
    conn.close()
    return _dicts(rows)


def log_event(user_id: int | None, event_name: str, meta: dict | None = None):
    event_name = (event_name or "").strip()
    if not event_name:
        return

    meta_json = json.dumps(meta or {}, ensure_ascii=False)

    conn = get_conn()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO event_logs (user_id, event_name, meta, created_at)
            VALUES (%s, %s, %s, %s)
        """, (user_id, event_name, meta_json, _now()))
    else:
        cur.execute("""
            INSERT INTO event_logs (user_id, event_name, meta, created_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, event_name, meta_json, _now()))

    conn.commit()
    conn.close()