import asyncio
import json
import os
import shutil
import sys
import threading
from pathlib import Path
from typing import Any, Coroutine

from agents import Agent, ModelSettings, Runner
from agents.mcp import MCPServerStdio
from dotenv import load_dotenv
import streamlit as st


APP_TITLE = "NovoDrive Motors"
APP_CAPTION = "NovaDrive Motors"
APP_IMAGE_PATH = "arquivos/novadrive.png"
CHAT_PLACEHOLDER = "Digite sua pergunta:"
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MCP_SERVER_SCRIPT = "servers/server_agente_atendente.py"


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def resolve_mcp_command() -> str:
    mcp_from_path = shutil.which("mcp")
    if mcp_from_path:
        return mcp_from_path

    scripts_dir = Path(sys.executable).resolve().parent
    candidates = ["mcp.exe", "mcp.cmd", "mcp"] if sys.platform == "win32" else ["mcp"]
    for candidate in candidates:
        command_path = scripts_dir / candidate
        if command_path.exists():
            return str(command_path)

    return "mcp"


def render_header() -> None:
    st.markdown(f"<h1 style='text-align: center;'>{APP_TITLE}</h1>", unsafe_allow_html=True)

    _, center_column, _ = st.columns(3)
    with center_column:
        st.image(APP_IMAGE_PATH, caption=APP_CAPTION)


def initialize_session_state() -> None:
    if "history" not in st.session_state:
        load_dotenv()
        st.session_state.history = []


def render_history() -> None:
    for message in st.session_state.history:
        message_type = message.get("role") or message.get("type")

        match message_type:
            case "user":
                with st.chat_message(message_type):
                    st.markdown(message["content"])
            case "assistant":
                with st.chat_message(message_type):
                    st.markdown(message["content"][0]["text"])
            case "function_call":
                if "transfer_to" not in message["name"]:
                    with st.chat_message(name="tool", avatar=":material/build:"):
                        st.markdown(f'LLM chamando tool {message["name"]}')
                        with st.expander("Visualizar argumentos"):
                            st.code(message["arguments"])
            case "function_call_output":
                try:
                    response = json.loads(message["output"])
                    with st.chat_message(name="tool", avatar=":material/data_object:"):
                        with st.expander("Visualizar resposta"):
                            st.code(response["text"])
                except (KeyError, TypeError, json.JSONDecodeError):
                    continue


def build_agent(name: str, handoff_description: str, instructions: str, handoffs: list[Agent] | None = None) -> Agent:
    resolved_handoffs = handoffs or []
    return Agent(
        name=name,
        model=MODEL_NAME,
        handoff_description=handoff_description,
        handoffs=resolved_handoffs,
        instructions=instructions,
        model_settings=ModelSettings(tool_choice="auto", temperature=0, parallel_tool_calls=False),
    )


def initialize_agents() -> None:
    if "agentRecepcao" in st.session_state:
        return

    maintenance_agent = build_agent(
        name="ManutencaoAssistente",
        handoff_description="Assistente de manutenção/revisão para clientes que já possuem veículo/carro.",
        instructions=(
            "Você é um assistente da NovaDrive Motors que deve ajudar o cliente a agendar uma visita para manutenção ou revisão. "
            "Pergunte o nome completo para identificar o cliente e então use as ferramentas para descobrir os veículos/carros que tem (get_info_cliente). "
            "Com base nisso colete as informações do que ele precisa, agende um horário na concessionária onde comprou o veículo (com agenda_visita_para_assistencia). "
            "Não é necessario escolher um vendedor, apenas agendar a visita na concessionária onde comprou o veículo/carro."
        ),
    )

    sales_agent = build_agent(
        name="VendasAssistente",
        handoff_description="Assistente para trativa de vendas, informações sobre veículos e agendamento de visitas/test drive.",
        instructions=(
            "Você é um assistente da NovaDrive Motors que deve ajudar e convencer o cliente a comprar um carro/veículo. "
            "Antes de tudo use a ferramenta get_veiculos_disponiveis para conhecer as opções disponíveis e apresentar a ele. "
            "Você pode fazer perguntas para entender o que o cliente precisa e oferecer as melhores opções de veículos/carros baseado na ferramenta que você chamou. "
            "Quando o cliente decidir, agende uma visita na concessionária mais próxima do cliente, para descobrir as concessionárias use get_concessionarias "
            "e para descobrir os vendedores dessa concessionária use get_vendedores_por_concessionaria. "
            "Então, agende a visita com a ferramenta agenda_visita_para_compra, onde você vai escolher o vendedor e a concessionária mais próxima do cliente."
        ),
    )

    reception_agent = build_agent(
        name="RecepcaoAssistente",
        handoff_description="Assistente de recepção e roteamento inicial do atendimento.",
        handoffs=[sales_agent, maintenance_agent],
        instructions=(
            "Você é um assistente de recepção da NovaDrive Motors, uma empresa nacional de veículos/carros do Brasil. "
            "Você é responsável pela recepção e deve apenas apresentar a empresa e oferecer as opções disponíveis. "
            "Apresente a NovaDrive Motors como empresa de veículos/carros e orgulhosamente brasileira. "
            "Mostre o site https://www.novadrivemotors.com.br/ para conhecer mais sobre a empresa. "
            "Ofereça para conhecer os carros e agendar uma visita com vendedor com possibilidade de test drive. "
            "Ou então no caso de querer manutenção ou revisão pode agendar uma visita a concessionária."
        ),
    )

    st.session_state.agentRecepcao = reception_agent
    st.session_state.agentVendas = sales_agent
    st.session_state.agenteManutencao = maintenance_agent
    st.session_state.current_agent = reception_agent


async def resolve_chat(
    current_agent: Agent,
    history: list[dict[str, Any]],
    sales_agent: Agent,
    maintenance_agent: Agent,
) -> tuple[Agent, list[dict[str, Any]]]:
    async with MCPServerStdio(params={"command": resolve_mcp_command(), "args": ["run", MCP_SERVER_SCRIPT]}) as server:
        sales_agent.mcp_servers = [server]
        maintenance_agent.mcp_servers = [server]

        result = await Runner.run(
            starting_agent=current_agent,
            input=history,
            context=history,
        )

        return result.last_agent, result.to_input_list()


def run_async_task(coro: Coroutine[Any, Any, tuple[Agent, list[dict[str, Any]]]]) -> tuple[Agent, list[dict[str, Any]]]:
    error: list[BaseException] = []
    output: list[tuple[Agent, list[dict[str, Any]]]] = []

    def _runner() -> None:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            output.append(loop.run_until_complete(coro))
        except BaseException as exc:  # pragma: no cover
            error.append(exc)
        finally:
            loop.close()

    worker = threading.Thread(target=_runner, daemon=False)
    worker.start()
    worker.join()

    if error:
        raise error[0]

    return output[0]


def handle_prompt() -> None:
    prompt = st.chat_input(CHAT_PLACEHOLDER)
    if not prompt:
        return

    st.session_state.history.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Pensando..."):
        current_agent = st.session_state.current_agent
        history = st.session_state.history
        sales_agent = st.session_state.agentVendas
        maintenance_agent = st.session_state.agenteManutencao

        last_agent, new_history = run_async_task(
            resolve_chat(current_agent, history, sales_agent, maintenance_agent)
        )

        st.session_state.current_agent = last_agent
        st.session_state.history = new_history
        st.rerun()


def render_active_agent_toast() -> None:
    if "current_agent" in st.session_state:
        st.toast(f"Agente atual: {st.session_state.current_agent.name}")


def run_app() -> None:
    render_header()
    initialize_session_state()
    render_history()
    initialize_agents()
    handle_prompt()
    render_active_agent_toast()