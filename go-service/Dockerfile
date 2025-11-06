FROM golang:1.21-alpine

WORKDIR /app

# Copy go.mod first
COPY go.mod ./

# Copy source code
COPY main.go ./
COPY PersianSwear.go ./
COPY data.txt ./

# Download dependencies and generate go.sum
# This needs to run after copying main.go to see what packages are needed
RUN go mod download
RUN go mod tidy

# Build
RUN go build -o main .

# Copy data.txt to runtime location (needed at runtime)
COPY data.txt /app/data.txt

# Run
EXPOSE 9000
CMD ["./main"]

