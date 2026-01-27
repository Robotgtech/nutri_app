from utils.db import init_db, add_allowed_email

init_db()

add_allowed_email("gabrielmateus.mg@gmail.com")
add_allowed_email("teste2@email.com")

print("Allowlist OK")
