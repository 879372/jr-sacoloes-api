#!/bin/bash
# Rodar migrações automaticamente no deploy usando python3
# --fake-initial resolve o erro de tabelas que já existem mas não estão registradas
python3 manage.py migrate --fake-initial
# Iniciar o servidor WSGI com Gunicorn usando o caminho do binário ou módulo
python3 -m gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
