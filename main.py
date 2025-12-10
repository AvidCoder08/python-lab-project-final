from streamlit.runtime.scriptrunner import get_script_run_ctx
import sys


# If this script is executed with plain `python main.py` there is no Streamlit
# ScriptRunContext and accessing streamlit.session_state or other runtime
# features produces lots of warnings.
# We detect that and exit with a helpful message so the noisy warnings stop.
if get_script_run_ctx() is None:
    print("This app must be started with Streamlit. Run:\n\n streamlit run main.py\n\nfrom your project root (not `python main.py`).")
    sys.exit(0)


import streamlit as st
from ui import AppUI


st.set_page_config(page_title="Python Lab MovieDB", layout="wide")




def main():
    ui = AppUI()
    ui.run()




if __name__ == "__main__":
    main()