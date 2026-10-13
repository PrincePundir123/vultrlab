"""Generate local secrets without printing them. Never overwrite an existing .env."""
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[2]
destination = root / ".env"
if destination.exists():
    raise SystemExit(".env already exists; edit it explicitly")
value = (root / ".env.example").read_text()
password = secrets.token_urlsafe(24)
value = value.replace("replace-with-random-password", password)
for marker in ("replace-with-at-least-32-random-characters", "replace-with-another-32-random-characters", "replace-with-strong-password"):
    while marker in value:
        value = value.replace(marker, secrets.token_urlsafe(32), 1)
destination.write_text(value)
print("Created .env. Read OPERATOR_PASSWORD locally; keep this file private.")
