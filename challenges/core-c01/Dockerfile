FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==3.1.0
COPY app/app.py /app/app.py
RUN mkdir -p /app/data && chown -R 10001:10001 /app/data
ENV CHALLENGE_ID=core-c01
USER 10001
CMD ["python","/app/app.py"]
