# 📌 API - Python 3.11.9

Esta API foi desenvolvida em **Python 3.11.9** e possui um único endpoint que atende às necessidades do sistema.

---

## 🚀 Endpoint

### `POST /api/model-risk`

#### 📥 Request (Exemplo)
```json
{
  "input_data": [
    {
      "fields": [
        "CustomerID",
        "CheckingStatus",
        "LoanDuration",
        "CreditHistory",
        "LoanPurpose",
        "LoanAmount",
        "ExistingSavings",
        "EmploymentDuration",
        "InstallmentPercent",
        "Sex",
        "OthersOnLoan",
        "CurrentResidenceDuration",
        "OwnsProperty",
        "Age",
        "InstallmentPlans",
        "Housing",
        "ExistingCreditsCount",
        "Job",
        "Dependents",
        "Telephone",
        "ForeignWorker"
      ],
      "values": [
        [
          "CUST-001",
          "A12",
          24,
          "A34",
          "car",
          12000,
          "A61",
          "A75",
          3,
          "male",
          "none",
          4,
          "A121",
          35,
          "none",
          "rent",
          1,
          "skilled",
          1,
          "yes",
          "yes"
        ]
      ]
    }
  ]
}
```

- **param1** *(string, obrigatório)* → Descrição do campo.  
- **param2** *(number, obrigatório)* → Descrição do campo.  

#### 📤 Response
```json
{
    "predictions": [
        {
            "fields": [
                "prediction",
                "probability"
            ],
            "values": [
                [
                    "No Risk",
                    [0.6758321523666382, 0.3241678774356842]
                ],
                [
                    "No Risk", 
                    [0.8493950366973877, 0.1506049484014511]
                ],
                [
                    "Risk",
                    [0.4720305800437927, 0.5279694199562073]
                ]
            ]
        }
    ]
}
```

- **predictions** *(string)* → Indica as predições feitas pelo modelo.  
- **predictions.fields** *(string)* → Indica os headers dos resultados.  
- **predictions.values** *(string/number)* → Retorno do processamento.  

---

## 🌐 Frontend

O repositório do frontend que consome esta API está disponível no seguinte link:  

👉 [Acessar Repositório do Frontend](https://github.com/vek03/AI-Soldiers-UI)

---

## 🛠️ Requisitos

- Python **3.11.9**  
- Dependências listadas em `requirements.txt`

---

## ▶️ Como rodar a API

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar servidor (exemplo com FastAPI + Uvicorn)
uvicorn main:app --reload
```
---
