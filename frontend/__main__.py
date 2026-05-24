"""Run the Streamlit frontend: python -m frontend"""

import sys
from pathlib import Path

from streamlit.web import cli as stcli

app_path = Path(__file__).parent / "app.py"
sys.argv = ["streamlit", "run", str(app_path), *sys.argv[1:]]
sys.exit(stcli.main())
