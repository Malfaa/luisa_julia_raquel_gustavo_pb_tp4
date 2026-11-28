from routes.classify import modelo, vectorizer

# usuários do banco de exemplo: admin/admin, jose/1234, maria/senha123

MENSAGEM = "I want a refund for my LG Smart TV because it stopped working."


def test_classify_sem_token(client):
    resposta = client.post("/classify", json={"message": MENSAGEM})

    assert resposta.status_code == 401
    assert resposta.headers["www-authenticate"] == "Bearer"


def test_classify_com_token_invalido(client):
    resposta = client.post(
        "/classify",
        json={"message": MENSAGEM},
        headers={"Authorization": "Bearer token.invalido.123"},
    )

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Token inválido ou expirado"}


def test_classify_retorna_intencao_e_probabilidade(client, obter_headers):
    resposta = client.post(
        "/classify",
        json={"message": MENSAGEM},
        headers=obter_headers("jose", "1234"),
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert set(corpo) == {"intent", "probability"}
    assert corpo["intent"] in list(modelo.classes_)
    assert 0 <= corpo["probability"] <= 1


def test_classify_bate_com_o_modelo_salvo(client, obter_headers):
    resposta = client.post(
        "/classify",
        json={"message": MENSAGEM},
        headers=obter_headers("admin", "admin"),
    )

    # a rota tem que devolver o mesmo que o modelo dá direto no joblib
    X = vectorizer.transform([MENSAGEM])
    assert resposta.json()["intent"] == modelo.predict(X)[0]
    assert resposta.json()["probability"] == round(float(modelo.predict_proba(X)[0].max()), 4)


def test_classify_rejeita_campo_extra(client, obter_headers):
    resposta = client.post(
        "/classify",
        json={"message": MENSAGEM, "debug": True},
        headers=obter_headers("jose", "1234"),
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"][0]["type"] == "extra_forbidden"


def test_classify_rejeita_corpo_sem_message(client, obter_headers):
    resposta = client.post("/classify", json={}, headers=obter_headers("jose", "1234"))

    assert resposta.status_code == 422
    assert resposta.json()["detail"][0]["type"] == "missing"


def test_classify_rejeita_mensagem_vazia_ou_so_com_espacos(client, obter_headers):
    headers = obter_headers("jose", "1234")

    for mensagem in ["", "   "]:
        resposta = client.post("/classify", json={"message": mensagem}, headers=headers)
        assert resposta.status_code == 422


def test_classify_rejeita_mensagem_muito_longa(client, obter_headers):
    resposta = client.post(
        "/classify",
        json={"message": "a" * 1001},
        headers=obter_headers("jose", "1234"),
    )

    assert resposta.status_code == 422


def test_classify_rejeita_tipo_errado(client, obter_headers):
    resposta = client.post(
        "/classify", json={"message": 123}, headers=obter_headers("jose", "1234")
    )

    assert resposta.status_code == 422
