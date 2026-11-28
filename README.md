# TP4 — Análise e Segurança de Agentes de IA

Projeto de Bloco: Análise e Segurança de Agentes de IA.

Este repositório contém a quarta entrega do projeto, desenvolvida a partir do TP3 utilizando o **Customer Support Ticket Dataset**. Nesta etapa foram adicionados o classificador de intenções otimizado com `GridSearchCV`, a exportação dos artefatos de ML para integração com a API FastAPI e o agente autônomo, além da estruturação do repositório para o log parcial de pentest adversarial.

## Objetivo

Consolidar a análise estatística dos TPs anteriores com a implementação e otimização do classificador de intenções via `GridSearchCV`, disponibilizar os modelos serializados para integração com a API FastAPI/agente autônomo e preparar o registro do pentest adversarial, mantendo os controles de segurança e testes automatizados desenvolvidos ao longo do projeto.

## Estrutura de pastas

```text
.
├── README.md
├── requirements.txt
├── data/
│   └── customer_support_tickets.csv
├── eda/
│   └── eda_tp3.ipynb
├── fastapi/
│   ├── database.db
│   ├── sqlite_database.py
│   ├── main.py
│   ├── agente/
│   │   ├── agente.py
│   │   ├── cliente_classify.py
│   │   └── demo_conversa.py
│   ├── routes/
│   ├── models/
│   │   ├── intent_classifier.joblib
│   │   ├── melhor_classificador.joblib
│   │   └── vectorizer.joblib
│   └── security/
├── pentest/
├── tests/
├── zap/
│   └── scan_passivo_zap_TP3.md
├── others/
│   └── planejamento.md
│   └── ...        Documentos complementares do projeto
└── .github/
    └── workflows/
        └── testes.yml
```

## Instalação

Requer Python 3.10 ou superior. Recomenda-se utilizar um ambiente virtual.

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### Linux/macOS

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Banco de dados

O projeto utiliza SQLite.

Para criar o banco e realizar a população inicial:

```bash
python fastapi/sqlite_database.py
```

O arquivo `database.db` fica localizado dentro de `fastapi/` e contém usuários e predições de exemplo pertencentes a usuários diferentes.

## EDA

O notebook com as etapas dos TP1, TP2, TP3 e TP4 está em:

```text
eda/eda_tp3.ipynb
```

Para executá-lo localmente:

```bash
jupyter notebook eda/eda_tp3.ipynb
```

No TP3 foram acrescentados o experimento de regressão linear, as métricas R² e RMSE, Residual Plot, Q-Q Plot e a formalização do problema de classificação de intenções.

### Classificação de Intenções (TP4)

No mesmo notebook (`eda/eda_tp3.ipynb`), a seção **2. TP4 — Classificador de Intenções e Otimização (Tarefas 1 e 3)** implementa o classificador multiclasse para `Ticket Type` (5 intenções):

- Preparação do texto combinando `Ticket Subject` e `Ticket Description` (com substituição de `{product_purchased}` por `Product Purchased`) e split estratificado 80/20.
- Comparação entre baseline (`DummyClassifier`), pipeline base (`CountVectorizer` + `LogisticRegression`) e modelo otimizado via `GridSearchCV` com validação cruzada estratificada (`StratifiedKFold`, 5 folds, `scoring="f1_macro"`).
- Avaliação com acurácia, F1-score (macro e weighted), ROC-AUC OvR macro, gráfico da curva ROC-AUC multiclasse (One-vs-Rest por classe), `classification_report` e matriz de confusão.
- Serialização via `joblib` em `fastapi/models/vectorizer.joblib`, `fastapi/models/melhor_classificador.joblib` e `fastapi/models/intent_classifier.joblib`.

## API

A partir da pasta `fastapi/`:

```bash
uvicorn main:app --reload
```

A API ficará disponível em:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

Principais rotas:

- `GET /health`
- `POST /auth/token`
- `POST /predict`
- `GET /predict/{id}`
- `POST /classify`

A API utiliza autenticação JWT, validação de ownership para prevenção de BOLA, modelos Pydantic com `extra='forbid'`, CORS com allowlist, headers HTTP de segurança e rate limiting no endpoint de autenticação.

Os artefatos `.joblib` do classificador de intenções já estão versionados em `fastapi/models/` para consumo pela rota `POST /classify`.

### POST /classify

Recebe uma mensagem em JSON, exige token JWT (`Authorization: Bearer ...`), transforma o texto com o `CountVectorizer` (`vectorizer.joblib`) e passa pelo classificador (`melhor_classificador.joblib`). Os dois arquivos são carregados uma vez, quando a API sobe.

```bash
# 1. obter o token
curl -X POST http://127.0.0.1:8000/auth/token -d "username=jose&password=1234"

# 2. classificar (troque TOKEN pelo access_token recebido)
curl -X POST http://127.0.0.1:8000/classify \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "I want a refund for my LG Smart TV because it stopped working."}'
```

Resposta (o valor varia conforme o modelo):

```json
{"intent": "Cancellation request", "probability": 0.4098}
```

O corpo aceita só o campo `message` (1 a 1000 caracteres, sem contar espaços das pontas). Campo extra, campo faltando ou mensagem vazia retornam `422`, e sem token válido a resposta é `401`.

### Agente de atendimento (Tarefa 4)

O código está em `fastapi/agente/`:

- `agente.py`: `Agent` com system prompt de atendimento ao cliente, a `@function_tool` `classificar_intencao` e a função `responder`, que roda cada turno com `Runner.run`. O agente usa `tool_use_behavior="stop_on_first_tool"` e `ModelSettings(tool_choice="classificar_intencao")`, então toda mensagem passa pelo classificador e a resposta é a saída da ferramenta, sem o LLM reescrever.
- `cliente_classify.py`: faz o login em `/auth/token` e chama `POST /classify` com o JWT (a ferramenta só consome o endpoint, não acessa o modelo direto).
- `demo_conversa.py`: conversa de 3 turnos, salva em `fastapi/agente/demo_conversa.md`.

O modelo de linguagem é o `openai/gpt-oss-20b` pela API gratuita do Groq (compatível com o Agents SDK). As chaves e credenciais ficam só em variáveis de ambiente:

```powershell
$env:GROQ_API_KEY="chave-do-groq"
$env:AGENTE_USUARIO="jose"
$env:AGENTE_SENHA="1234"
```

Com a API rodando (`uvicorn main:app --port 8000` dentro de `fastapi/`), em outro terminal, também dentro de `fastapi/`:

```bash
python -m agente.demo_conversa
```

Se a API estiver em outro endereço (por exemplo, o do Cloudflare Tunnel), defina `URL_API`.

Exemplo de execução (saída completa em `fastapi/agente/demo_conversa.md`):

| Turno | Mensagem do cliente | Resposta do agente |
| :---: | :--- | :--- |
| 1 | Hello, I bought a LG Smart TV and it stopped working after two days. | Intenção: Technical issue (probabilidade: 0.49) |
| 2 | I want my money back, please. | Intenção: Technical issue (probabilidade: 0.48) |
| 3 | Actually, I think I was charged twice for it. | Intenção: Product inquiry (probabilidade: 0.61) |

**Limitação:** a demonstração valida a integração (agente → ferramenta → `POST /classify` com JWT → modelo). As intenções previstas nem sempre fazem sentido porque o desempenho do classificador, medido no notebook, é próximo do acaso (acurácia de cerca de 21% e ROC-AUC OvR de cerca de 0,50 no conjunto de teste, para 5 classes).

## Testes automatizados

Os testes estão localizados em `tests/` e utilizam `pytest` e o `TestClient` do FastAPI.

A suíte cobre cenários de autenticação, autorização/BOLA, validação de entrada, rate limiting e acesso a rotas protegidas, além da rota `POST /classify` (JWT, formato da resposta e validação do corpo) e do cliente que o agente usa para chamá-la (sem usar a API do Groq).

Para executar:

```bash
pytest tests/ -v
```

## GitHub Actions

O workflow de integração contínua está em:

```text
.github/workflows/testes.yml
```

A cada push, o GitHub Actions instala as dependências do projeto e executa:

```bash
pytest tests/ -v
```

As execuções podem ser acompanhadas na aba **Actions** do repositório.

## OWASP ZAP

A auditoria final da API é realizada com OWASP ZAP.

O relatório exportado fica na pasta `zap/` e a análise dos findings Medium e High está documentada em:

```text
zap/scan_passivo_zap_TP3.md
```

## Pentest

O diretório `pentest/` está estruturado para armazenar o relatório em PDF dos 12 testes adversariais (pentest) e suas respectivas evidências.

## Cloudflare Tunnel

Para disponibilizar temporariamente a API por HTTPS durante a preparação dos testes adversariais, foi utilizado o Cloudflare Tunnel:

```bash
cloudflared tunnel --url http://localhost:8000
```

A URL gerada no TP3 está registrada em `others/planejamento.md`.

## Repositório

https://github.com/Malfaa/luisa_julia_raquel_gustavo_pb_tp4

## Declaração de Uso de IA

Em conformidade com as diretrizes do projeto, declaramos explicitamente o uso de ferramentas de IA como apoio técnico nas atividades do TP4:

### Etapa de ML e EDA (Tarefas 1 e 3)
Uso da ferramenta de IA **Gemini (Google)** como apoio técnico nas seguintes atividades:
- Estruturação do pipeline de classificação multiclasse em `scikit-learn` (`CountVectorizer` + `LogisticRegression`);
- Configuração da busca de hiperparâmetros com `GridSearchCV` e validação cruzada estratificada (`StratifiedKFold`);
- Geração do código de cálculo das métricas, tabela comparativa, matrizes de confusão e gráfico da curva ROC-AUC multiclasse (OvR);
- Serialização dos artefatos `.joblib` e organização do repositório (`pentest/.gitkeep`, atualização de `requirements.txt` e `README.md`).

Todo o código, os experimentos e os artefatos serializados (`.joblib`) foram validados por meio de execução real do notebook ponta a ponta e verificação automatizada da suíte de testes.

### Etapa de API e agente (Tarefas 2 e 4)
Uso da ferramenta de IA **Claude (Anthropic)** como apoio técnico no desenvolvimento da rota `POST /classify`, e dos testes automatizados dessas partes.

## Integrantes

- Luisa Hering Bell de Otero
- Júlia Reinke
- Raquel Braga dos Santos
- Gustavo Malfa Corrêa
