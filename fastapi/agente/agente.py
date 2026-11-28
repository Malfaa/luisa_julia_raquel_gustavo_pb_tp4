import os

import requests
from agents import (
    Agent,
    ModelSettings,
    OpenAIChatCompletionsModel,
    Runner,
    function_tool,
    set_tracing_disabled,
)
from agente.cliente_classify import classificar_texto
from openai import AsyncOpenAI

# sem chave da OpenAI o SDK tentaria enviar traces e ficaria dando aviso
set_tracing_disabled(True)

BASE_URL_GROQ = "https://api.groq.com/openai/v1"
MODELO_GROQ = "openai/gpt-oss-20b"

instructions = """
Você é um agente especializado em atendimento ao cliente.
Sempre classifique a intenção da mensagem usando a ferramenta classificar_intencao.
Seja educado.
Seja objetivo.
Não invente informações.
"""


def classificar_mensagem(texto: str) -> str:
    try:
        resultado = classificar_texto(texto)
    except (requests.RequestException, RuntimeError) as erro:
        return f"Não foi possível classificar a mensagem: {erro}"

    return f"Intenção: {resultado['intent']} (probabilidade: {resultado['probability']:.2f})"


@function_tool
def classificar_intencao(texto: str) -> str:
    """Classifica a intenção de uma mensagem de cliente chamando o endpoint POST /classify da API.

    Args:
        texto: mensagem enviada pelo cliente.
    """
    return classificar_mensagem(texto)


def configurar_agente(base_url: str = BASE_URL_GROQ) -> Agent:
    client = AsyncOpenAI(
        api_key=os.environ["GROQ_API_KEY"],  # a chave fica só na variável de ambiente
        base_url=base_url,
    )

    model = OpenAIChatCompletionsModel(model=MODELO_GROQ, openai_client=client)

    return Agent(
        name="Atendente",
        model=model,
        instructions=instructions,
        tools=[classificar_intencao],
        # devolve a saída da ferramenta direto, sem o LLM reescrever (resposta determinística)
        tool_use_behavior="stop_on_first_tool",
        # obriga o agente a chamar a ferramenta em toda mensagem
        model_settings=ModelSettings(tool_choice="classificar_intencao"),
    )


async def responder(agent: Agent, historico: list, mensagem: str):
    """Roda um turno da conversa. Devolve a resposta e o histórico atualizado."""
    entrada = historico + [{"role": "user", "content": mensagem}]
    resultado = await Runner.run(agent, entrada)
    return resultado.final_output, resultado.to_input_list()
