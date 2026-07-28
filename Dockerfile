FROM tiangolo/uwsgi-nginx-flask:python3.12

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN python3 -m pip install --no-cache-dir --upgrade -r /app/requirements.txt

ENV LISTEN_PORT=8080 \
    PYTHONUNBUFFERED=1

EXPOSE 8080

COPY ./uwsgi.ini /app/uwsgi.ini
COPY ./app.py /app/app.py
COPY ./templates /app/templates
COPY ./static /app/static

RUN mkdir -p /instance/avatars /instance/court_media /instance/social_thumbnails \
    && ln -s /instance /app/instance

VOLUME ["/instance"]
