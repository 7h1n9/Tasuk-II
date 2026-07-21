FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==3.1.0
COPY challenges/common/advanced_app.py /app/app.py
ENV CHALLENGE_ID=core-a04
USER 10001
CMD ["python","/app/app.py"]
