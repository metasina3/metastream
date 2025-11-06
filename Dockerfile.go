# Go Microservice Dockerfile
FROM golang:1.21-alpine

WORKDIR /app

# Copy go mod files
COPY go-service/go.mod go-service/go.sum ./
RUN go mod download

# Copy source code
COPY go-service/ ./go-service/

# Build
RUN cd go-service && go build -o /app/main .

# Run
EXPOSE 9000
CMD ["/app/main"]

