FROM node:20-alpine AS build
WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /frontend/dist /usr/share/nginx/html
# Copy pdfjs worker as plain .js so nginx serves it without .mjs MIME issues
COPY --from=build /frontend/node_modules/pdfjs-dist/build/pdf.worker.min.js /usr/share/nginx/html/pdf.worker.min.js

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
