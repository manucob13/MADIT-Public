import json
import base64
import requests
import streamlit as st
from datetime import datetime


# ── GitHub config ──────────────────────────────────────────────────────────────
def _headers():
    return {
        "Authorization": f"Bearer {st.secrets['github']['token']}",
        "Accept": "application/vnd.github+json",
    }

def _repo_base():
    owner = st.secrets["github"]["owner"]
    repo  = st.secrets["github"]["private_repo"]
    return f"https://api.github.com/repos/{owner}/{repo}"


# ── Leer el índice ─────────────────────────────────────────────────────────────
def _get_index() -> tuple[list, str | None]:
    """Lee Quotes/index.json del repo privado. Devuelve (data, sha)."""
    url = f"{_repo_base()}/contents/Quotes/index.json"
    r   = requests.get(url, headers=_headers())
    if r.status_code == 404:
        return [], None
    r.raise_for_status()
    content = base64.b64decode(r.json()["content"]).decode()
    sha     = r.json()["sha"]
    return json.loads(content), sha


# ── Guardar el índice ──────────────────────────────────────────────────────────
def _save_index(data: list, sha: str | None, message: str):
    url     = f"{_repo_base()}/contents/Quotes/index.json"
    content = base64.b64encode(
        json.dumps(data, indent=2, ensure_ascii=False).encode()
    ).decode()
    payload = {"message": message, "content": content}
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=_headers(), json=payload)
    r.raise_for_status()


# ── Guardar el Excel original ──────────────────────────────────────────────────
def _upload_excel(filename: str, file_bytes: bytes):
    url     = f"{_repo_base()}/contents/Quotes/{filename}"
    content = base64.b64encode(file_bytes).decode()
    # Verificar si ya existe (para obtener sha)
    r_check = requests.get(url, headers=_headers())
    payload = {
        "message": f"Upload quote {filename}",
        "content": content,
    }
    if r_check.status_code == 200:
        payload["sha"] = r_check.json()["sha"]
    r = requests.put(url, headers=_headers(), json=payload)
    r.raise_for_status()


# ── Función principal: guardar quote ──────────────────────────────────────────
def save_quote(
    client:       str,
    contact:      str,
    title:        str,
    date:         str,
    meta:         dict,
    items,
    margin_pct:   float,
    distributor:  str,
    uploaded_file,           # el archivo subido por el usuario
) -> dict:
    """
    Guarda la quote en MADIT-Private:
    - Sube el Excel original a Quotes/
    - Añade una entrada al índice Quotes/index.json
    """

    # Nombre único del archivo
    date_clean = date.replace("/", "")
    client_clean = client.replace(" ", "_").replace("/", "-")
    quote_num  = meta.get("quote_number", "NOQUOTE")
    filename   = f"{date_clean}_{client_clean}_{quote_num}.xlsx"

    # Subir el Excel original
    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    _upload_excel(filename, file_bytes)

    # Leer índice actual
    index, sha = _get_index()

    # Crear registro
    record = {
        "id":           f"{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "date":         date,
        "client":       client,
        "contact":      contact,
        "title":        title,
        "quote_number": meta.get("quote_number", "—"),
        "expiry":       meta.get("expiry", "—"),
        "currency":     meta.get("currency", "AUD"),
        "distributor":  distributor,
        "margin_pct":   margin_pct,
        "cost_total":   round(float(items["Total Cost"].sum()), 2),
        "sell_total":   round(float(items["Total Cost"].sum() / (1 - margin_pct / 100)), 2),
        "filename":     filename,
    }

    index.append(record)
    _save_index(index, sha, f"Add quote {quote_num} for {client}")

    return record


# ── Cargar historial ───────────────────────────────────────────────────────────
def load_quotes() -> list:
    """Devuelve todas las quotes guardadas."""
    index, _ = _get_index()
    return index


# ── Descargar Excel de una quote ───────────────────────────────────────────────
def download_quote_excel(filename: str) -> bytes:
    """Descarga el Excel original de una quote guardada."""
    url = f"{_repo_base()}/contents/Quotes/{filename}"
    r   = requests.get(url, headers=_headers())
    r.raise_for_status()
    return base64.b64decode(r.json()["content"])


# ── Lista de clientes únicos ───────────────────────────────────────────────────
def get_clients() -> list[str]:
    index = load_quotes()
    return sorted(set(q["client"] for q in index if q.get("client")))
