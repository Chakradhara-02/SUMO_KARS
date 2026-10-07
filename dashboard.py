"""Compatibility entry point for the simulation studio."""
import subprocess
import sys
import urllib.request
import streamlit as st
import streamlit.components.v1 as components
from kars.models import ROOT

st.set_page_config(page_title='KARS Simulation Studio',layout='wide')
url='http://127.0.0.1:8765'
try:
    with urllib.request.urlopen(url+'/api/scenarios',timeout=1) as response:
        connected=response.status==200
except OSError:
    connected=False
if connected:
    st.link_button('Open Simulation Studio in a full window',url)
    components.iframe(url,height=1200,scrolling=True)
else:
    st.title('KARS Simulation Studio')
    if st.button('Start Simulation Studio',type='primary'):
        logs=ROOT/'outputs/console'
        logs.mkdir(parents=True,exist_ok=True)
        flags={'creationflags':subprocess.CREATE_NO_WINDOW} if sys.platform=='win32' else {}
        with (logs/'server.log').open('a',encoding='utf-8') as log:
            subprocess.Popen([sys.executable,str(ROOT/'main.py'),'serve'],cwd=ROOT,
                             stdout=log,stderr=subprocess.STDOUT,**flags)
        st.success('Starting the simulation console. Open http://127.0.0.1:8765.')
    st.code(r'.\sumo_env\Scripts\python.exe main.py serve',language='powershell')
