FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source and build the production assets
COPY . .
RUN npm run build

# Expose the port Railway assigns dynamically
EXPOSE 80

# Serve the 'dist' folder, enable single-page-app routing (--single), and bind to the dynamic port
CMD ["sh", "-c", "npx sirv-cli dist --port ${PORT:-80} --host 0.0.0.0 --single"]
