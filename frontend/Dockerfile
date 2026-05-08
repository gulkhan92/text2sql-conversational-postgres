# Build + serve frontend using Vite
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

# Serve the built assets
RUN npm install -g serve

COPY --from=build /app/dist ./dist
EXPOSE 5173

# Using `serve` on port 5173 to match docker-compose port mapping
CMD ["serve", "-s", "dist", "-l", "5173"]
