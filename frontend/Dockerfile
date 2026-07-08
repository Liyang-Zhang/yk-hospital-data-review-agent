FROM node:22-bookworm-slim AS build

WORKDIR /app

ARG NPM_REGISTRY=https://registry.npmmirror.com
ARG VITE_API_BASE=/api/v1

ENV VITE_API_BASE=${VITE_API_BASE}

COPY package.json package-lock.json ./
RUN npm config set registry ${NPM_REGISTRY} && npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
