@echo off
echo 🚀 Starting CarIActerologie in PRODUCTION mode...
set APP_ENV=production
set DEBUG=false
echo Environment: %APP_ENV%
echo Branch: production
streamlit run my_streamlit_app.py --server.port 8502