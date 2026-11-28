import pytest
import requests
from agente import cliente_classify


class RespostaFalsa:
    def __init__(self, status_code, corpo):
        self.status_code = status_code
        self._corpo = corpo

    def json(self):
        return self._corpo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


@pytest.fixture(autouse=True)
def ambiente(monkeypatch):
    monkeypatch.setenv("AGENTE_USUARIO", "jose")
    monkeypatch.setenv("AGENTE_SENHA", "1234")
    monkeypatch.setenv("URL_API", "http://api-falsa")
    # cada teste começa sem token guardado
    monkeypatch.setattr(cliente_classify, "_token", None)


def test_faz_login_e_chama_classify_com_o_token(monkeypatch):
    chamadas = []

    def post_falso(url, **kwargs):
        chamadas.append((url, kwargs))
        if url.endswith("/auth/token"):
            return RespostaFalsa(200, {"access_token": "abc"})
        return RespostaFalsa(200, {"intent": "Refund request", "probability": 0.41})

    monkeypatch.setattr(cliente_classify.requests, "post", post_falso)

    resultado = cliente_classify.classificar_texto("I want a refund")

    assert resultado == {"intent": "Refund request", "probability": 0.41}
    url, kwargs = chamadas[1]
    assert url == "http://api-falsa/classify"
    assert kwargs["json"] == {"message": "I want a refund"}
    assert kwargs["headers"] == {"Authorization": "Bearer abc"}
    assert kwargs["timeout"] == cliente_classify.TIMEOUT


def test_reaproveita_o_token_entre_mensagens(monkeypatch):
    logins = []

    def post_falso(url, **kwargs):
        if url.endswith("/auth/token"):
            logins.append(url)
            return RespostaFalsa(200, {"access_token": "abc"})
        return RespostaFalsa(200, {"intent": "Billing inquiry", "probability": 0.3})

    monkeypatch.setattr(cliente_classify.requests, "post", post_falso)

    cliente_classify.classificar_texto("primeira")
    cliente_classify.classificar_texto("segunda")

    assert len(logins) == 1


def test_renova_o_token_quando_a_api_responde_401(monkeypatch):
    tokens_usados = []

    def post_falso(url, **kwargs):
        if url.endswith("/auth/token"):
            return RespostaFalsa(200, {"access_token": f"token{len(tokens_usados)}"})
        tokens_usados.append(kwargs["headers"]["Authorization"])
        if len(tokens_usados) == 1:
            return RespostaFalsa(401, {"detail": "Token inválido ou expirado"})
        return RespostaFalsa(200, {"intent": "Billing inquiry", "probability": 0.3})

    monkeypatch.setattr(cliente_classify.requests, "post", post_falso)
    monkeypatch.setattr(cliente_classify, "_token", "token_velho")

    resultado = cliente_classify.classificar_texto("oi")

    assert resultado["intent"] == "Billing inquiry"
    assert tokens_usados == ["Bearer token_velho", "Bearer token1"]


def test_sem_credenciais_nao_tenta_chamar_a_api(monkeypatch):
    monkeypatch.delenv("AGENTE_SENHA")

    def post_falso(url, **kwargs):
        raise AssertionError("não era pra chamar a API")

    monkeypatch.setattr(cliente_classify.requests, "post", post_falso)

    with pytest.raises(RuntimeError, match="AGENTE_USUARIO e AGENTE_SENHA"):
        cliente_classify.classificar_texto("oi")


def test_mensagem_formata_a_saida_do_classify(monkeypatch):
    from agente import agente

    monkeypatch.setattr(
        agente,
        "classificar_texto",
        lambda texto: {"intent": "Refund request", "probability": 0.4098},
    )

    assert agente.classificar_mensagem("oi") == "Intenção: Refund request (probabilidade: 0.41)"


def test_mensagem_avisa_quando_a_api_falha(monkeypatch):
    from agente import agente

    def falha(texto):
        raise requests.ConnectionError("API fora do ar")

    monkeypatch.setattr(agente, "classificar_texto", falha)

    assert agente.classificar_mensagem("oi").startswith(
        "Não foi possível classificar a mensagem"
    )
