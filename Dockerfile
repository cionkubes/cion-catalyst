FROM python:3.6-alpine

WORKDIR /opt/catalyst

COPY requirements.txt .
RUN pip install -r requirements.txt --src /lib

COPY src .

CMD ["python", "catalyst.py"]
