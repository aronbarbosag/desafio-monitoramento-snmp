FROM node:20-alpine AS builder

WORKDIR /app

# Instala as dependências antes de copiar o código: camada só invalida quando
# package.json/package-lock.json mudam, não a cada edição de código-fonte.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
