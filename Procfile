web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --worker-class gthread
release: python manage.py migrate --fake-initial && python manage.py collectstatic --noinput
