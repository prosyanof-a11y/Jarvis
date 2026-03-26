FROM node:22-slim

WORKDIR /app

# Зависимости для better-sqlite3 и sharp
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY package*.json ./
RUN npm install --omit=dev

COPY . .

RUN mkdir -p data

CMD ["node", "src/index.js"]
