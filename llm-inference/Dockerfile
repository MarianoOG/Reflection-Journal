# Stage 1: Download the model
FROM python:3.12-slim AS model-downloader
RUN pip install --no-cache-dir huggingface-hub[cli] gpt-oss
RUN hf download openai/gpt-oss-20b --exclude "metal/*" "original/*" --local-dir /model-cache


# Stage 2: Runtime with vLLM
FROM vllm/vllm-openai:v0.10.2

# Copy the downloaded model from the first stage
COPY --from=model-downloader /model-cache /gpt-oss-20b

ENV HF_HUB_OFFLINE=1
EXPOSE 8080

ENTRYPOINT python3 -m vllm.entrypoints.openai.api_server \
  --port 8080 \
  --model /gpt-oss-20b \
  --gpu-memory-utilization 0.85 \
  --max-model-len 65536 \
  ${API_KEY:+--api-key "$API_KEY"}
