try:
	from streamlit_agents.app_core import run_app
except ModuleNotFoundError:
	from app_core import run_app

run_app()
