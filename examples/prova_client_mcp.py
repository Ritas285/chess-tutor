#!/usr/bin/env python3
"""Prova il server MCP di Chess Tutor COME FAREBBE UN ALTRO PROGRAMMA (un "host"): lancia il server come sottoprocesso (stdio),
elenca tool, resource e prompt e li usa. Stesso schema di Lezione13/mcp_consume_demo.py (S13).

    python examples/prova_client_mcp.py

Serve OPENAI_API_KEY nel file .env (la ricerca e la verifica usano il modello; l'elenco dei tool no).
"""
import asyncio
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

RADICE = Path(__file__).resolve().parent.parent


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(RADICE / "mcp_server.py")], cwd=str(RADICE))
    async with Client(stdio_client(params)) as client:
        tools = await client.list_tools()
        print("TOOL:", [t.name for t in tools.tools])
        print("PROMPT:", [p.name for p in (await client.list_prompts()).prompts])

        r = await client.call_tool("cerca_conoscenza", {"ramo": "rules", "domanda": "Come funziona l'arrocco?", "k": 2})
        print("\ncerca_conoscenza(rules, arrocco):\n" + r.content[0].text[:500] + " …")

        for risposta in ("Il cavallo si muove a L e può saltare sugli altri pezzi.", "Il cavallo si muove in diagonale."):
            r = await client.call_tool("verifica_risposta", {"domanda": "Come si muove il cavallo?", "risposta": risposta})
            print(f"\nverifica_risposta({risposta!r}):\n  -> {r.content[0].text}")

        doc = await client.read_resource("corpus://rules/01_pezzi_e_movimenti.md")
        print("\nresource corpus://rules/01_pezzi_e_movimenti.md:\n" + doc.contents[0].text[:120] + " …")


if __name__ == "__main__":
    asyncio.run(main())
