FROM tiangolo/uwsgi-nginx-flask:python3.12

ARG APP_UID=1654

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN python3 -m pip install --no-cache-dir --upgrade -r /app/requirements.txt

ENV LISTEN_PORT=8080 \
    PYTHONUNBUFFERED=1

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4).close()"]

COPY ./uwsgi.ini /app/uwsgi.ini
COPY ./app.py /app/app.py
COPY ./data /app/data
COPY ./templates /app/templates
COPY ./static /app/static

RUN mkdir -p \
        /instance/avatars \
        /instance/court_media \
        /instance/social_thumbnails \
        /var/cache/nginx \
        /var/lib/nginx \
    && rm -f /app/main.py /app/prestart.sh \
    && ln -s /instance /app/instance \
    && sed -i '/^chown-socket/d' /etc/uwsgi/uwsgi.ini \
    && chown -R "$APP_UID:0" \
        /app \
        /etc/nginx \
        /instance \
        /run \
        /var/cache/nginx \
        /var/lib/nginx \
        /var/log/nginx \
        /var/log/supervisor

VOLUME ["/instance"]

USER $APP_UID
