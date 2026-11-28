from pathlib import Path

import joblib
from models.database_models import User
from models.schemas import ClassifyRequest, ClassifyResponse
from security.dependencies import get_current_user

from fastapi import APIRouter, Depends

classify_router = APIRouter(tags=["Classificação"])

# Os artefatos são carregados uma vez, quando a API sobe, e não a cada requisição
# (o treino foi feito no notebook eda/eda_tp3.ipynb).
PASTA_MODELOS = Path(__file__).resolve().parents[1] / "models"
vectorizer = joblib.load(PASTA_MODELOS / "vectorizer.joblib")
modelo = joblib.load(PASTA_MODELOS / "melhor_classificador.joblib")


@classify_router.post(
    "/classify",
    response_model=ClassifyResponse,
    summary="Classifica a intenção de uma mensagem com o modelo treinado",
    responses={
        200: {"description": "Intenção prevista e probabilidade"},
        401: {"description": "Token JWT ausente, inválido ou expirado"},
        422: {"description": "Corpo inválido (campo faltando, extra ou mensagem vazia)"},
    },
)
def classify(
    data: ClassifyRequest,
    usuario: User = Depends(get_current_user),
):
    """
    Recebe uma mensagem, transforma o texto com o CountVectorizer e passa pelo
    classificador salvo com joblib. Retorna a intenção prevista e a probabilidade
    dessa classe. Requer autenticação Bearer Token (JWT).
    """
    texto_vetorizado = vectorizer.transform([data.message])

    intent = modelo.predict(texto_vetorizado)[0]
    probabilidade = modelo.predict_proba(texto_vetorizado)[0].max()

    return {"intent": str(intent), "probability": round(float(probabilidade), 4)}
