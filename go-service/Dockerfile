FROM golang:1.21-alpine

WORKDIR /app

# Copy go.mod first
COPY go.mod ./

# Copy source code
COPY main.go ./

# Download dependencies and generate go.sum
# This needs to run after copying main.go to see what packages are needed
RUN go mod download
RUN go mod tidy

# Build
RUN go build -o main .

# Run
EXPOSE 9000
CMD ["./main"]

