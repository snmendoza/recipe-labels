ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install system deps
RUN apk add --no-cache \
    python3 \
    py3-pip \
    cups-client \
    font-dejavu \
    jq \
    gcc \
    musl-dev \
    python3-dev \
    jpeg-dev \
    zlib-dev

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY app/ ./app/
COPY run.sh /

RUN chmod a+x /run.sh

CMD ["/run.sh"]
