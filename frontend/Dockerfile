FROM node:20-slim
WORKDIR /app
COPY frontend/package.json ./package.json
RUN npm install
COPY frontend /app
ENV HOST=0.0.0.0
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
