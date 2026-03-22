import os
import boto3
import pymysql
from flask import Flask, request, jsonify, render_template
from botocore.exceptions import ClientError

app = Flask(__name__)

# Configurações AWS (Buckets)
RAW_BUCKET = 'lab-avancado-raw-images-estudos'
PROCESSED_BUCKET = 'lab-avancado-processed-images-estudos'
REGION = 'us-east-1' # Ajuste conforme sua região

# Configurações RDS
DB_HOST = 'seu-rds-endpoint.amazonaws.com'
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

def get_db_connection():
    """Estabelece conexão com o MySQL no RDS."""
    password = get_db_password()
    if not password:
        raise Exception("Não foi possível obter a senha do banco de dados.")
    
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=password,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db():
    """Cria a tabela de usuários se não existir."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nome VARCHAR(100) NOT NULL,
                    bio TEXT,
                    foto_url VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()
        conn.close()
        print("Tabela 'usuarios' verificada/criada com sucesso.")
    except Exception as e:
        print(f"Erro ao inicializar banco de dados: {e}")

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

    # 2. Salvar metadados no RDS
    # A URL da foto aponta para o bucket PROCESSADO (onde a Lambda salvará o thumbnail)
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

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=3000, debug=True)
