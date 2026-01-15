FROM python:3.11-slim

# Install system dependencies (TexLive for LaTeX, etc.)
RUN apt-get update && apt-get install -y \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-latex-extra \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Playwright browsers (Chromium only to save space, with deps)
# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Install pdflatex module separately to bypass outdated attrs dependency conflict
RUN pip install --no-cache-dir pdflatex --no-deps
RUN python -m playwright install --with-deps chromium

# Copy application code
ENV CACHE_BUST=1
COPY . .

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
