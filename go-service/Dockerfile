FROM golang:1.21-alpine

# Build arguments for proxy (optional)
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG http_proxy
ARG https_proxy
ARG NO_PROXY

# Set proxy environment variables if provided
ENV HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    http_proxy=${http_proxy} \
    https_proxy=${https_proxy} \
    NO_PROXY=${NO_PROXY}

# Configure Go proxy settings if HTTP_PROXY is set
# Go uses GOPROXY environment variable, but also respects HTTP_PROXY/HTTPS_PROXY
RUN if [ -n "$HTTP_PROXY" ]; then \
        echo "Using proxy for Go module downloads: $HTTP_PROXY"; \
    else \
        echo "No proxy configured, using direct connection"; \
    fi

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

