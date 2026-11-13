FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY . .
RUN npm run build
ENV VITE_API_TARGET=http://backend-java:8080
EXPOSE 5173
CMD ["npm", "run", "preview"]
