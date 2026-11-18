# --- builder: compila el binario Rust ---
FROM rust:1-bookworm AS builder
WORKDIR /app
COPY Cargo.toml ./
COPY src ./src
COPY tests ./tests
RUN cargo build --release --bin preventa-middleware

# --- runtime: imagen mínima con el binario + certificados TLS ---
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /app/target/release/preventa-middleware /usr/local/bin/preventa-middleware
# el store persistente vive en /app/data (montar como volumen)
RUN mkdir -p /app/data
ENV STORE_PATH=/app/data/store.json
EXPOSE 3000
CMD ["preventa-middleware"]
