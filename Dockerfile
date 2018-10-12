FROM python:3.6

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

EXPOSE 20-21 21100-21110

CMD ["python", "server.py"]
