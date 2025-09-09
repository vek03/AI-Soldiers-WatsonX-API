import os
import json
import requests
from typing import Any, Dict, List, Tuple
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# ---- OpenAI SDK (GPT) ----
try:
    from openai import OpenAI
except Exception as e:
    raise RuntimeError("Instale: pip install openai>=1.0.0") from e

# Carrega variáveis do .env
load_dotenv()

# Watsonx (opcional)
API_KEY = os.getenv("API_KEY")
WATSON_URL = os.getenv("WATSON_URL")
DEPLOYMENT_ID = os.getenv("DEPLOYMENT_ID")
MODEL_ID = os.getenv("MODEL_ID")

# GPT
GPT_API_KEY = os.getenv("GPT_API_KEY")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o-mini")

if not GPT_API_KEY:
    raise RuntimeError("Defina GPT_API_KEY no .env")

# OpenAI client
gpt_client = OpenAI(api_key=GPT_API_KEY)

app = FastAPI(title="Model Risk API (Watsonx + GPT)")

# CORS
origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:4200").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Watsonx helpers (existente, opcional) ----------------
def gerar_iam_token() -> str:
    url = "https://iam.cloud.ibm.com/identity/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": API_KEY}
    r = requests.post(url, data=data, headers=headers)
    print(f"[DEBUG] Token status: {r.status_code}")
    print(f"[DEBUG] Token response: {r.text[:1000]}...")
    r.raise_for_status()
    return r.json()["access_token"]

def chamar_model_risk(payload: Dict[str, Any]) -> Dict[str, Any]:
    token = gerar_iam_token()
    url = f"{WATSON_URL}/ml/v4/deployments/{DEPLOYMENT_ID}/predictions?version=2021-05-01"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    print(f"[DEBUG] URL chamada: {url}")
    print(f"[DEBUG] Payload enviado (Watsonx): {json.dumps(payload)[:1500]}...")

    r = requests.post(url, headers=headers, json=payload)
    print(f"[DEBUG] Status Watsonx: {r.status_code}")
    print(f"[DEBUG] Resposta Watsonx: {r.text[:1500]}...")
    r.raise_for_status()
    return r.json()

# ---------------- GPT helpers (novo; emula saída predictions) ----------------

def _zip_fields_values(fields: List[str], values_row: List[Any]) -> Dict[str, Any]:
    n = min(len(fields), len(values_row))
    return {fields[i]: values_row[i] for i in range(n)}

def _normalize_payload_to_rows(payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    """
    Aceita:
      - {"input_data": [{"fields": [...], "values": [[...], [...]]}]}
      - dict único (um registro)
      - list[dict] (vários registros)
    Retorna lista de linhas como dict e uma string de debug sobre o formato detectado.
    """
    if isinstance(payload, dict) and "input_data" in payload:
        try:
            block = payload["input_data"][0]
            fields = block.get("fields", [])
            values = block.get("values", [])
            rows = [_zip_fields_values(fields, row) for row in values]
            return rows, "formato=input_data(fields+values)"
        except Exception:
            pass

    if isinstance(payload, dict):
        return [payload], "formato=dict(singular)"

    if isinstance(payload, list) and all(isinstance(x, dict) for x in payload):
        return payload, "formato=list[dict]"

    return [{"raw": payload}], "formato=desconhecido(raw)"

# Prompt que força JSON puro com o schema esperado.
# NÃO menciona domínio (crédito, etc). Apenas mapeia entrada -> rótulo + probabilidade.
GPT_SYSTEM_INSTRUCTIONS = """
Você é um gerador de predições. Dado um conjunto de registros (cada registro é um dicionário
de atributos), você deve produzir SOMENTE um JSON no schema:

{
  "predictions": [
    {
      "fields": ["prediction", "probability"],
      "values": [
        ["<string>", <float entre 0 e 1>],
        ...
      ]
    }
  ]
}

Regras:
- A quantidade de linhas em "values" DEVE ser exatamente igual ao número de registros recebidos.
- "prediction" é um rótulo qualquer derivado dos atributos.
- "probability" é um número float entre 0 e 1 (use 2 a 4 casas decimais).
- Não retorne NADA além do JSON válido.
"""

def _build_user_prompt(rows: List[Dict[str, Any]]) -> str:
    return json.dumps({"records": rows}, ensure_ascii=False)

def chamar_gpt_predicoes(payload: Dict[str, Any]) -> Dict[str, Any]:
    rows, fmt = _normalize_payload_to_rows(payload)
    print(f"[DEBUG] Payload normalizado ({fmt}). Registros: {len(rows)}")

    messages = [
        {"role": "system", "content": GPT_SYSTEM_INSTRUCTIONS.strip()},
        {"role": "user", "content": _build_user_prompt(rows)},
    ]

    def _call_gpt(json_mode: bool):
        kwargs = {
            "model": GPT_MODEL,
            "temperature": 0.0,
            "messages": messages,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return gpt_client.chat.completions.create(**kwargs)

    try:
        try:
            completion = _call_gpt(json_mode=True)
        except Exception as e1:
            print(f"[ERROR] GPT json_mode failed: {repr(e1)}")
            completion = _call_gpt(json_mode=False)

        raw = completion.choices[0].message.content.strip()
        print(f"[DEBUG] GPT raw: {raw[:500]}")

        parsed = None
        try:
            parsed = json.loads(raw)
        except Exception:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                snippet = raw[start:end+1]
                parsed = json.loads(snippet)

        if not parsed or "predictions" not in parsed:
            values = [["class_A", 0.5] for _ in rows]
            parsed = {
                "predictions": [
                    {"fields": ["prediction", "probability"], "values": values}
                ]
            }

        return {
            "ok": True,
            "engine": "gpt",
            "model": GPT_MODEL,
            "predictions": parsed.get("predictions", [])
        }

    except Exception as e:
        import traceback
        print("[ERROR] GPT call failed:", repr(e))
        traceback.print_exc()
        return {"ok": False, "engine": "gpt", "error": f"{type(e).__name__}: {e}"}


@app.post("/api/model-risk")
async def model_risk(request: Request, engine: str = Query(default="gpt", pattern="^(gpt|watson)$")):
    try:
        payload = await request.json()
        if not payload:
            return JSONResponse(status_code=400, content={"error": "Corpo da requisição vazio"})

        if engine == "watson":
            try:
                resultado = chamar_model_risk(payload)
                # Encapsula para manter consistência com o retorno gpt
                return JSONResponse(content={"ok": True, "engine": "watson", "result": resultado})
            except requests.exceptions.HTTPError as http_err:
                return JSONResponse(status_code=500, content={"ok": False, "engine": "watson", "error": f"HTTP Error: {str(http_err)}"})
            except Exception as e:
                return JSONResponse(status_code=500, content={"ok": False, "engine": "watson", "error": str(e)})

        # engine == "gpt"
        resultado = chamar_gpt_predicoes(payload if isinstance(payload, dict) else {"dados": payload})
        if not resultado.get("ok"):
            return JSONResponse(status_code=500, content=resultado)
        return JSONResponse(content=resultado)

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
