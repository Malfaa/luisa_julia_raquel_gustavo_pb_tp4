import os

import requests

TIMEOUT = 5  # segundos

# o token fica guardado aqui para não fazer login a cada mensagem
# (o /auth/token tem rate limit de 10 por minuto)
_token = None


def _url_api() -> str:
    return os.getenv("URL_API", "http://localhost:8000")


def _obter_token() -> str:
    usuario = os.getenv("AGENTE_USUARIO")
    senha = os.getenv("AGENTE_SENHA")
    if not usuario or not senha:
        raise RuntimeError(
            "Defina as variáveis de ambiente AGENTE_USUARIO e AGENTE_SENHA"
        )

    resposta = requests.post(
        f"{_url_api()}/auth/token",
        data={"username": usuario, "password": senha},
        timeout=TIMEOUT,
    )
    resposta.raise_for_status()
    return resposta.json()["access_token"]


def _post_classify(texto: str) -> requests.Response:
    return requests.post(
        f"{_url_api()}/classify",
        json={"message": texto},
        headers={"Authorization": f"Bearer {_token}"},
        timeout=TIMEOUT,
    )


def classificar_texto(texto: str) -> dict:
    """Chama POST /classify com JWT e devolve {"intent": ..., "probability": ...}."""
    global _token

    if _token is None:
        _token = _obter_token()

    resposta = _post_classify(texto)

    # o token dura 30 minutos, então pode ter expirado no meio da conversa
    if resposta.status_code == 401:
        _token = _obter_token()
        resposta = _post_classify(texto)

    resposta.raise_for_status()
    return resposta.json()
