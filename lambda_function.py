import boto3
import os
import sys
import io
from PIL import Image

# Configuração do cliente S3
s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    Acionado quando um objeto é criado no bucket RAW.
    Corta a imagem em um quadrado 300x300 e salva no bucket PROCESSED.
    """
    
    # Bucket de destino (definido via variável de ambiente na Lambda)
    dest_bucket = os.environ.get('DEST_BUCKET', 'lab-avancado-processed-images-estudos')
    
    for record in event['Records']:
        # Pegar informações do arquivo que disparou o evento
        source_bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        # Definir o caminho de saída (removendo o prefixo 'raw/' se existir)
        file_name = key.split('/')[-1]
        dest_key = f"processed/{file_name}"
        
        print(f"Processando imagem: {key} do bucket {source_bucket}")
        
        try:
            # 1. Baixar a imagem do S3 para a memória
            response = s3.get_object(Bucket=source_bucket, Key=key)
            image_content = response['Body'].read()
            
            # 2. Abrir imagem com Pillow
            img = Image.open(io.BytesIO(image_content))
            
            # 3. Lógica de corte para Quadrado Perfeito (Center Crop)
            width, height = img.size
            new_size = min(width, height)
            
            left = (width - new_size) / 2
            top = (height - new_size) / 2
            right = (width + new_size) / 2
            bottom = (height + new_size) / 2
            
            img = img.crop((left, top, right, bottom))
            
            # 4. Redimensionar para 300x300 (Thumbnail)
            img = img.resize((300, 300), Image.LANCZOS)
            
            # 5. Salvar a imagem processada em um buffer
            buffer = io.BytesIO()
            # Manter o formato original ou converter para JPEG
            format = img.format if img.format else 'JPEG'
            img.save(buffer, format=format)
            buffer.seek(0)
            
            # 6. Upload para o bucket de destino
            s3.put_object(
             Bucket=dest_bucket,
             Key=dest_key,
             Body=buffer,
             ContentType=f'image/{format.lower()}'
         )
            
            print(f"Sucesso! Imagem salva em: {dest_bucket}/{dest_key}")
            
        except Exception as e:
            print(f"Erro ao processar imagem {key}: {e}")
            raise e

    return {
        'statusCode': 200,
        'body': 'Imagens processadas com sucesso!'
    }
