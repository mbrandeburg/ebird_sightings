FROM --platform=$BUILDPLATFORM python:3.11-alpine AS build
RUN pip install --upgrade pip

RUN apk --no-cache add curl

WORKDIR /app

COPY requirements.txt /app
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements.txt

# Will be mounted in for sqlite persistence as a PV
VOLUME /mnt

COPY . /app

RUN adduser -D worker
RUN chown -R worker:worker /mnt/

USER worker
WORKDIR /app

COPY --chown=worker:worker . .

ENTRYPOINT ["python3"]
CMD ["main.py"]