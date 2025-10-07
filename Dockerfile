# Use the official Node.js image
FROM node:18-alpine

# Set the working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the application
COPY . .

# Create the output directory
RUN mkdir -p out

# Command to run the script
CMD ["node", "scrape_quran_all.mjs"]
