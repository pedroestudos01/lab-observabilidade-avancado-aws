import os
import boto3
import pymysql
import math
from flask import Flask, request, jsonify, render_template
from botocore.exceptions import ClientError

app = Flask(__name__)

# --- Configurações AWS ---
# Confirme se estes são os nomes exatos dos seus buckets criados no S3!
RAW_BUCKET = 'lab-avancado-raw-images-estudos'
PROCESSED_BUCKET = 'lab-avancado-processed-images-estudos'
REGION = 'us-east-1'

# --- Configurações RDS ---
DB_HOST = 'lab-avancado-db.c8fak4e4wiz3.us-east-1.rds.amazonaws.com'
DB_USER = 'admin'
DB_NAME = 'perfil_db'

def get_db_password():
    """Busca a senha do RDS no SSM Parameter Store."""
    ssm = boto3.client('ssm', region_name=REGION)
    try:
        parameter = ssm.get_parameter(Name='/lab2/db/password', WithDecryption=True)
        return parameter['Parameter']['Value']
    except ClientError as e:
        print(f"Erro ao buscar senha no SSM: {e}")
        return None

def get_base_connection():
    """Conecta ao servidor MySQL globalmente, sem especificar um banco."""
    password = get_db_password()
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=password,
        cursorclass=pymysql.cursors.DictCursor
    )

def get_db_connection():
    """Conecta especificamente ao banco 'perfil_db' para o uso diário."""
    password = get_db_password()
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=password,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db():
    """Cria o banco de dados e a tabela se eles não existirem."""
    try:
        # 1. Usa a conexão global para CRIAR a "sala" (banco de dados)
        conn_base = get_base_connection()
        with conn_base.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        conn_base.commit()
        conn_base.close()

        # 2. Entra na "sala" recém-criada e constrói a tabela de usuários
        conn_db = get_db_connection()
        with conn_db.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nome VARCHAR(100) NOT NULL,
                    bio TEXT,
                    foto_url VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn_db.commit()
        conn_db.close()
        print(f"Banco '{DB_NAME}' e tabela 'usuarios' prontos para uso!")
    except Exception as e:
        print(f"Erro crítico ao inicializar o banco de dados: {e}")
        
@app.route('/stress')
def stress_cpu():
    """Rota criada exclusivamente para fritar a CPU e testar o Auto Scaling"""
    resultado = 0
    # Faz a CPU calcular a raiz quadrada de 5 milhões de números
    for i in range(5000000):
        resultado += math.sqrt(i)
    return jsonify({"message": "CPU estressada com sucesso!", "calculo": resultado})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/perfis', methods=['POST'])
def cadastrar_perfil():
    """Recebe dados do formulário e salva no S3 e RDS."""
    nome = request.form.get('nome')
    bio = request.form.get('bio')
    foto = request.files.get('foto')

    if not nome or not foto:
        return jsonify({"error": "Nome e Foto são obrigatórios"}), 400

    # 1. Upload da imagem original para o Bucket RAW
    s3 = boto3.client('s3', region_name=REGION)
    file_name = f"raw/{nome.replace(' ', '_')}_{foto.filename}"
    
    try:
        s3.upload_fileobj(foto, RAW_BUCKET, file_name)
    except ClientError as e:
        return jsonify({"error": f"Erro no upload S3: {e}"}), 500

    # 2. Salvar metadados no RDS apontando para a foto PROCESSADA
    foto_url_processada = f"https://{PROCESSED_BUCKET}.s3.amazonaws.com/processed/{file_name.split('/')[-1]}"
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "INSERT INTO usuarios (nome, bio, foto_url) VALUES (%s, %s, %s)"
            cursor.execute(sql, (nome, bio, foto_url_processada))
        conn.commit()
        conn.close()
    except Exception as e:
        return jsonify({"error": f"Erro no banco de dados: {e}"}), 500

    return jsonify({"message": "Perfil cadastrado com sucesso!", "foto_url": foto_url_processada}), 201

@app.route('/api/perfis', methods=['GET'])
def listar_perfis():
    """Lista todos os perfis cadastrados."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT nome, bio, foto_url FROM usuarios ORDER BY created_at DESC")
            perfis = cursor.fetchall()
        conn.close()
        return jsonify(perfis)
    except Exception as e:
        return jsonify({"error": f"Erro ao listar perfis: {e}"}), 500

# Executa a criação do banco assim que o código sobe
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)