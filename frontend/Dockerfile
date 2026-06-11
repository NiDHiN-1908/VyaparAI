# frontend/Dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package configurations
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose Next.js default port
EXPOSE 3000

# Start dev server
CMD ["npm", "run", "dev"]
