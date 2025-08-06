@echo off
echo 🧪 Starting CarIActerologie in DEVELOPMENT mode...
set APP_ENV=development
set DEBUG=true
echo Environment: %APP_ENV%
echo Branch: development
streamlit run my_streamlit_app.py --server.port 8501