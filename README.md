# Docker Flask Application

A simple Flask web application containerized with Docker.

## Build and Run

```bash
# Build the image
docker build -t flask-app .

# Run the container
docker run -d -p 5000:5000 --name flask-container flask-app

# Access the app
curl http://localhost:5000
```

## Stop and Clean Up

```bash
# Stop the container
docker stop flask-container

# Remove the container
docker rm flask-container

# Remove the image
docker rmi flask-app
```
