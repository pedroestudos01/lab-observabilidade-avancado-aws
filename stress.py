import requests
import concurrent.futures
import time
import sys

# URL da aplicação (ajuste para o seu Load Balancer ou IP Público)
TARGET_URL = "http://ALB-App-Lab-avancado-1095200832.us-east-1.elb.amazonaws.com/stress"

# Configurações do Stress Test
TOTAL_REQUESTS = 500
CONCURRENT_THREADS = 50

def send_request(request_id):
    """Envia uma requisição GET simples para a página inicial."""
    try:
        start_time = time.time()
        response = requests.get(TARGET_URL, timeout=5)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            print(f"[Req {request_id}] Sucesso - {duration:.2f}s")
            return True
        else:
            print(f"[Req {request_id}] Falha (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"[Req {request_id}] Erro: {e}")
        return False

def start_chaos():
    print(f"--- Iniciando Canhão de Caos em {TARGET_URL} ---")
    print(f"Alvo: {TOTAL_REQUESTS} requisições com {CONCURRENT_THREADS} threads simultâneas.\n")
    
    start_total = time.time()
    success_count = 0
    
    # Usando ThreadPoolExecutor para simular múltiplos usuários simultâneos
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_THREADS) as executor:
        # Mapeia as requisições
        futures = [executor.submit(send_request, i) for i in range(TOTAL_REQUESTS)]
        
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                success_count += 1
                
    end_total = time.time()
    
    print("\n--- Relatório de Stress ---")
    print(f"Tempo Total: {end_total - start_total:.2f} segundos")
    print(f"Requisições com Sucesso: {success_count}/{TOTAL_REQUESTS}")
    print(f"Taxa de Sucesso: {(success_count/TOTAL_REQUESTS)*100:.1f}%")
    print(f"Média de Req/s: {TOTAL_REQUESTS / (end_total - start_total):.2f}")

if __name__ == "__main__":
    if "seu-load-balancer" in TARGET_URL:
        print("AVISO: Você precisa editar o script stress.py e colocar a URL real do seu Load Balancer!")
        sys.exit(1)
        
    start_chaos()
