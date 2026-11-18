"""Step 3: come è organizzato il coding agent. AGENTS.md, skill e collegamento MCP devono dire cose VERE: si controllano contro il repository.

Un'istruzione che cita un comando o un file che non esistono è peggio di nessuna istruzione: l'agente la segue e sbaglia."""
import asyncio
import json
import re
import sys
from pathlib import Path

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

RADICE = Path(__file__).resolve().parent.parent
AGENTS = (RADICE / "AGENTS.md").read_text(encoding="utf-8")
SKILL_ATTESE = {"add-rag-branch", "write-chess-content", "run-evals", "security-retest"}
TOOL_MCP = {"cerca_conoscenza", "verifica_risposta", "genera_quiz", "verifica_quiz", "verifica_mossa", "mosse_legali"}


def percorsi_citati(testo: str) -> set[str]:
    """I percorsi di file citati tra apici inversi (`evals/run_evals.py`, `chess_tutor/tutor.py`…), senza quelli generici o futuri."""
    trovati = set(re.findall(r"`((?:evals|chess_tutor|tests|app_pages|observability|examples|data|\.claude)/[\w./\-]+?\.(?:py|json|md|yml))`", testo))
    return trovati


# ---------- AGENTS.md ----------
def test_ogni_file_citato_in_agents_md_esiste():
    mancanti = [p for p in percorsi_citati(AGENTS) if not (RADICE / p).exists()]
    assert not mancanti, f"AGENTS.md cita file che non esistono: {mancanti}"


def test_ogni_comando_python_di_agents_md_punta_a_uno_script_che_esiste():
    comandi = re.findall(r"^(?:python|streamlit run) ([\w./\-]+\.py)", AGENTS, flags=re.M)
    assert {"evals/verifica_contenuti.py", "evals/run_evals.py", "evals/valuta_verifica.py", "evals/valuta_quiz.py",
            "app.py", "mcp_server.py"} <= set(comandi)
    assert [c for c in comandi if not (RADICE / c).exists()] == []


def test_i_moduli_della_mappa_del_codice_esistono():
    righe = AGENTS.split("## Mappa del codice")[1].split("## Regole")[0]
    moduli = re.findall(r"`([a-z_]+)\.py`", righe)
    assert len(moduli) >= 14
    mancanti = [m for m in moduli if not any((RADICE / d / f"{m}.py").exists() for d in ("chess_tutor", ".", "evals"))]
    assert not mancanti, f"nella mappa del codice ma non nel repository: {mancanti}"


def test_agents_md_ha_le_regole_che_non_si_violano_e_le_trappole():
    for frase in ("Niente mosse inventate", "dato, non istruzione", "Niente segreti", "citano la fonte", "licenza libera",
                  "Regola A/B", "Goodhart", "Trappole già incontrate", "solo il titolo"):
        assert frase in AGENTS, frase
    assert "Co-Authored" not in AGENTS or "righe di attribuzione" in AGENTS          # niente istruzione ad aggiungere l'attribuzione


def test_agents_md_non_contiene_segreti():
    assert not re.search(r"sk-[A-Za-z0-9_-]{16,}", AGENTS)
    assert "OPENAI_API_KEY=" not in AGENTS


def test_agents_md_elenca_i_tool_mcp_veri():
    for tool in TOOL_MCP:
        assert f"`{tool}`" in AGENTS, tool


def test_il_file_di_istruzioni_di_copilot_rimanda_ad_agents_md():
    assert "AGENTS.md" in (RADICE / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")


# ---------- le skill ----------
def test_le_quattro_skill_esistono_e_sono_ben_formate():
    cartelle = {p.name for p in (RADICE / ".claude" / "skills").iterdir() if p.is_dir()}
    assert cartelle == SKILL_ATTESE
    for nome in SKILL_ATTESE:
        testo = (RADICE / ".claude" / "skills" / nome / "SKILL.md").read_text(encoding="utf-8")
        intestazione = re.match(r"^---\nname: (.+)\ndescription: (.+)\n---\n", testo.replace("\r\n", "\n"))
        assert intestazione, f"{nome}: intestazione non valida"
        assert intestazione.group(1) == nome and len(intestazione.group(2)) > 40
        assert len(testo.split("---", 2)[2].strip()) > 300, f"{nome}: troppo corta per servire"


def test_le_skill_citano_solo_file_che_esistono():
    for nome in SKILL_ATTESE:
        testo = (RADICE / ".claude" / "skills" / nome / "SKILL.md").read_text(encoding="utf-8")
        mancanti = [p for p in percorsi_citati(testo) if not (RADICE / p).exists()]
        assert not mancanti, f"{nome} cita file che non esistono: {mancanti}"
    for tool_o_script in ("evals/verifica_contenuti.py", "evals/run_evals.py", "evals/retest_sicurezza.py"):
        assert (RADICE / tool_o_script).exists()


def test_agents_md_elenca_le_skill_che_ci_sono():
    righe = AGENTS.split("## Skill disponibili")[1].split("## MCP")[0]
    assert all(f"`{s}`" in righe for s in SKILL_ATTESE)


def test_la_skill_per_i_contenuti_rimanda_al_controllo_che_funziona_davvero():
    testo = (RADICE / ".claude" / "skills" / "write-chess-content" / "SKILL.md").read_text(encoding="utf-8")
    assert "python evals/verifica_contenuti.py" in testo and "maiuscole" in testo


# ---------- il collegamento MCP ----------
def test_i_file_di_collegamento_mcp_sono_validi_e_puntano_al_server():
    claude = json.loads((RADICE / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["chess-tutor"]
    assert claude["args"] == ["mcp_server.py"] and claude["command"].startswith(".venv/")
    vscode = json.loads((RADICE / ".vscode" / "mcp.json").read_text(encoding="utf-8"))["servers"]["chess-tutor"]
    assert vscode["type"] == "stdio" and vscode["args"] == ["${workspaceFolder}/mcp_server.py"]
    assert vscode["command"] == "${workspaceFolder}/" + claude["command"]            # stesso Python nei due host
    assert (RADICE / "mcp_server.py").exists()


def test_git_non_ignora_i_file_che_devono_stare_nel_repository():
    ignorati = (RADICE / ".gitignore").read_text(encoding="utf-8")
    assert "!.vscode/mcp.json" in ignorati and ".env" in ignorati.splitlines()          # mcp.json sì, la chiave mai
    assert ".mcp.json" not in ignorati.splitlines() and "AGENTS.md" not in ignorati and ".claude" not in ignorati


def avvia_e_elenca(comando: str, args: list[str]) -> set[str]:
    async def _run():
        params = StdioServerParameters(command=comando, args=args, cwd=str(RADICE))
        async with Client(stdio_client(params)) as client:
            return {t.name for t in (await client.list_tools()).tools}
    return asyncio.run(_run())


def test_il_server_parte_con_i_parametri_di_mcp_json_e_offre_i_sei_strumenti():
    """Fa ciò che farebbe l'host: lancia il comando di `.mcp.json` dalla radice del progetto e chiede l'elenco degli strumenti."""
    config_host = json.loads((RADICE / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["chess-tutor"]
    comando = RADICE / config_host["command"]
    if not comando.exists():                              # altro sistema operativo o ambiente diverso: si prova con il Python corrente
        comando = Path(sys.executable)
    assert avvia_e_elenca(str(comando), config_host["args"]) == TOOL_MCP
