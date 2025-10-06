# src/rag/validator.py

import json
from jsonschema import validate, Draft202012Validator
from jsonschema.exceptions import ValidationError
from pathlib import Path

SCHEMA_PATH = Path("src/schemas/legal_answer.schema.json")
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

def validate_answer_json(obj: dict) -> None:
    v = Draft202012Validator(SCHEMA)
    errors = sorted(v.iter_errors(obj), key=lambda e: e.path)
    if errors:
        msgs = [f"{'/'.join([str(p) for p in e.path])}: {e.message}" for e in errors]
        raise ValidationError(" | ".join(msgs))
