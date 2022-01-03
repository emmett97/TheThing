from datetime import datetime, timezone
import os.path
import subprocess
import json

def encrypt_cipher(password, random_num, ski, cipher_key):
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "cipher.js"))
    value = subprocess.check_output(
        ["node", script_path, password, random_num, ski, cipher_key])
    value = value.strip().decode()
    return value

def iso_date():
    date = datetime.now(timezone.utc)
    return date.isoformat()[:23] + "Z"

def find_inbetween(
    source: str,
    substring: str,
    substring2: str,
    json_parse: bool = False
):
    value = source \
        .split(substring, 1)[1] \
        .split(substring2, 1)[0]
    if json_parse:
        value = json.loads(value)
    return value