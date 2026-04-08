#!/bin/bash
# Rodar migrações automaticamente no deploy
python manage.py migrate
# Iniciar o servidor WSGI com Gunicorn
gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
