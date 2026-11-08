FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend /app/backend
COPY --from=frontend /frontend/dist /app/frontend/dist
COPY start-production.sh /app/start-production.sh
RUN chmod +x /app/start-production.sh
ENV APP_ENV=production
ENV FRONTEND_DIST_DIR=/app/frontend/dist
ENV HOST=0.0.0.0
WORKDIR /app
EXPOSE 8000
CMD ["/app/start-production.sh"]
