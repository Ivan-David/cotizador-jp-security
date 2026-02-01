# cotizador-jp-security
App para cotización de sistemas CCTV

Instrucciones rápidas:

- Instalar dependencias: `pip install -r requirements.txt`
- Ejecutar la app: `streamlit run app.py`

Tests y CI:

- Ejecutar tests localmente: `pytest -q`
- Un workflow de GitHub Actions (`.github/workflows/ci.yml`) corre los tests en cada PR.

Branch y PRs:

- Rama usada para estos cambios sugeridos: `feat/ui-improvements` (si se creó en tu repo remoto). Si quieres que abra el PR por ti, necesito permisos de push al remoto o que ejecutes el push desde tu entorno.

Notas:
- Coloca `logo.png` en la raíz para mostrar el logo en la sidebar y en el PDF.
