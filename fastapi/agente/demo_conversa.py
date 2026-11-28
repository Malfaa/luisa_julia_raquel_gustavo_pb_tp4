"""Demonstração de conversa com 3 turnos.

Antes de rodar, a API precisa estar no ar (uvicorn main:app --port 8000) e as
variáveis GROQ_API_KEY, AGENTE_USUARIO e AGENTE_SENHA precisam estar definidas.
Rodar a partir da pasta fastapi/:  python -m agente.demo_conversa
"""

import asyncio
from pathlib import Path

from agente.agente import configurar_agente, responder

MENSAGENS = [
    "Hello, I bought a LG Smart TV and it stopped working after two days.",
    "I want my money back, please.",
    "Actually, I think I was charged twice for it.",
]

ARQUIVO_SAIDA = Path(__file__).resolve().parent / "demo_conversa.md"


async def main():
    agent = configurar_agente()
    historico = []
    linhas = ["# Demonstração do agente (3 turnos)", ""]

    for turno, mensagem in enumerate(MENSAGENS, start=1):
        resposta, historico = await responder(agent, historico, mensagem)

        print(f"Turno {turno}")
        print(f"Cliente: {mensagem}")
        print(f"Agente:  {resposta}\n")

        linhas += [
            f"## Turno {turno}",
            f"**Cliente:** {mensagem}",
            "",
            f"**Agente:** {resposta}",
            "",
        ]

    ARQUIVO_SAIDA.write_text("\n".join(linhas), encoding="utf-8")
    print(f"Conversa salva em {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    asyncio.run(main())
