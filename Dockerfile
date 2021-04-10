FROM python:3.7-alpine

WORKDIR /code

COPY requirements_dev.txt .

RUN apk update && apk upgrade && \
    apk add --no-cache git build-base python3-dev libffi-dev jpeg-dev zlib-dev

RUN pip install -r requirements_dev.txt

COPY . /code

CMD ["python", "manager.py", "runserver"]
