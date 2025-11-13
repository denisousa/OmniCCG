FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y git curl python3-venv pip && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    apt-get install -y default-jre curl unzip

RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

RUN curl -L -o /tmp/freetxl.tar.gz https://txl.ca/download/25536-txl10.8b.linux64.tar.gz && \
    mkdir -p /opt/txl && \
    tar -xzf /tmp/freetxl.tar.gz -C /opt/txl --strip-components=1 && \
    chmod +x /opt/txl/bin/txl && \
    ln -sf /opt/txl/bin/txl /usr/local/bin/txl && \
    rm /tmp/freetxl.tar.gz

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY . .

RUN poetry config virtualenvs.create false

RUN poetry lock
RUN poetry install --no-interaction --no-ansi

EXPOSE 5000

CMD ["python3", "main.py"]



