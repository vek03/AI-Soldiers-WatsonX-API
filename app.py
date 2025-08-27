import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Carrega variáveis do .env
load_dotenv()

API_KEY = os.getenv("API_KEY")
WATSON_URL = os.getenv("WATSON_URL")
DEPLOYMENT_ID = os.getenv("DEPLOYMENT_ID")
MODEL_ID = os.getenv("MODEL_ID")

app = FastAPI(title="Model Risk API")

# Permitir requisições do Angular
origins = [
    "http://localhost:4200",  # endereço do seu Angular
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # quem pode acessar
    allow_credentials=True,      # cookies/autenticação
    allow_methods=["*"],         # GET, POST, OPTIONS etc
    allow_headers=["*"],         # Content-Type, Authorization etc
)

def gerar_iam_token():
    url = "https://iam.cloud.ibm.com/identity/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": API_KEY
    }
    r = requests.post(url, data=data, headers=headers)
    print(f"[DEBUG] Token status: {r.status_code}")
    print(f"[DEBUG] Token response: {r.text}")
    r.raise_for_status()
    return r.json()["access_token"]

def chamar_model_risk(payload):
    token = gerar_iam_token()
    url = f"{WATSON_URL}/ml/v4/deployments/{DEPLOYMENT_ID}/predictions?version=2021-05-01"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print(f"[DEBUG] URL chamada: {url}")
    print(f"[DEBUG] Payload enviado: {payload}")

    r = requests.post(url, headers=headers, json=payload)
    print(f"[DEBUG] Status Watsonx: {r.status_code}")
    print(f"[DEBUG] Resposta Watsonx: {r.text}")
    r.raise_for_status()
    return r.json()

@app.post("/api/model-risk")
async def model_risk(request: Request):
    try:
        payload = await request.json()
        if not payload:
            return JSONResponse(status_code=400, content={"error": "Corpo da requisição vazio"})
        resultado = chamar_model_risk(payload)
        return resultado
    except requests.exceptions.HTTPError as http_err:
        return JSONResponse(status_code=500, content={"error": f"HTTP Error: {str(http_err)}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
