FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==3.1.0
COPY app/app.py /app/app.py
ENV CHALLENGE_ID=core-a02
USER 10001
CMD ["python", "/app/app.py"]
