FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
RUN useradd -m lunex
USER lunex
ENV LUNEX_ENV=production PORT=8000
EXPOSE 8000
CMD ["python", "-m", "lunex"]
