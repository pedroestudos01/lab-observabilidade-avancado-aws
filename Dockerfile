# Usa o Python oficial e mais leve
FROM python:3.14-slim

# Define a pasta de trabalho lá dentro
WORKDIR /app

# Copia os arquivos da sua máquina para dentro do container
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do seu código
COPY . .

# Expõe a porta 80
EXPOSE 80

# Roda o Gunicorn (Servidor de Produção) apontando para o app.py na porta 80
CMD ["gunicorn", "--bind", "0.0.0.0:80", "app:app"]