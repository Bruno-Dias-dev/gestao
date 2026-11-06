FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements-mysql.txt ./
RUN pip install --no-cache-dir -r requirements-mysql.txt
COPY backend ./backend
WORKDIR /app/backend
EXPOSE 5000
CMD ["python", "run.py"]
