#!/bin/bash
# Rodar migrações automaticamente no deploy usando python3
python3 manage.py migrate
# Iniciar o servidor WSGI com Gunicorn usando o caminho do binário ou módulo
python3 -m gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
