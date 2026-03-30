FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
COPY wait-for-it.sh /wait-for-it.sh

RUN pip install --no-cache-dir -r requirements.txt
RUN chmod +x /wait-for-it.sh

COPY . .

EXPOSE 8000

CMD ["/wait-for-it.sh", "db:5432", "--", "python", "open_meteo_mcp_server.py"]