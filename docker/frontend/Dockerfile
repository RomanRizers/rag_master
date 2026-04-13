FROM node:20-alpine AS build
WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /frontend/dist /usr/share/nginx/html
# Copy pdfjs worker to a known root path
COPY --from=build /frontend/node_modules/pdfjs-dist/build/pdf.worker.min.mjs /usr/share/nginx/html/pdf.worker.min.mjs

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
