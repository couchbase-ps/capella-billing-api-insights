# Dev-server run model (matches the sibling project): the container runs Vite on 0.0.0.0:5173
# and proxies /api and /health to BACKEND_URL (the backend service on the compose network).
FROM node:24-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci
COPY . .

# predev copies node_modules/@couchbaselabs/topology-ui/images into public/topology-ui/images.
ENV BACKEND_URL=http://backend:8000
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
