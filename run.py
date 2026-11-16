import os
import pandas as pd
import concurrent.futures

# Importa a função diretamente do seu arquivo (sem precisar de subprocess.run)
# Isso exige que o run.py e o calc_metrics.py estejam na mesma pasta
from calc_metrics import process_pcap 

CAMINHO = "pcaps"
CLIENT_IP = "192.168.10.1"

def extrair_features(tarefa):
    """Worker que chama a função nativa e retorna um dicionário com os dados."""
    caminho_pcap, serv, cat = tarefa
    try:
        # Chama a função de processamento que já escrevemos
        row = process_pcap(caminho_pcap, CLIENT_IP, serv, cat)
        return row
    except Exception as e:
        print(f"Erro ao processar {caminho_pcap}: {e}")
        return None

def main():
    if not os.path.exists(CAMINHO):
        print(f"Erro: O diretório '{CAMINHO}' não existe.")
        return

    pastas = [item for item in os.listdir(CAMINHO) if os.path.isdir(os.path.join(CAMINHO, item))]
    tarefas = []

    # Mapeia as tarefas
    for pasta in pastas:
        try:
            serv, cat = pasta.split("-", 1)
        except ValueError:
            continue
            
        dir_pasta = os.path.join(CAMINHO, pasta)
        arqs = [item for item in os.listdir(dir_pasta) if item.endswith('.pcap')]
        
        for arq in arqs:
            caminho_pcap = os.path.join(dir_pasta, arq)
            tarefas.append((caminho_pcap, serv, cat))

    total = len(tarefas)
    print(f"Iniciando extração nativa de {total} arquivos usando {os.cpu_count()} núcleos...")

    resultados_validos = []

    # Processamento paralelo na RAM (Seguro e sem I/O de disco concorrente)
    with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futuros = {executor.submit(extrair_features, t): t for t in tarefas}
        
        concluidos = 0
        for futuro in concurrent.futures.as_completed(futuros):
            concluidos += 1
            row = futuro.result()
            if row is not None:
                resultados_validos.append(row)
            
            # Print de progresso a cada 100 arquivos para não poluir o terminal
            if concluidos % 100 == 0 or concluidos == total:
                print(f"Progresso: {concluidos}/{total} concluídos.")

    # Apenas o processo principal salva o arquivo (Fim das Condições de Corrida)
    if resultados_validos:
        print("\nGravando dataset final no disco...")
        df_final = pd.DataFrame(resultados_validos)
        df_final.to_csv("dataset.csv", index=False)
        print(f"Sucesso! Dataset criado com {len(df_final)} capturas validadas.")
    else:
        print("Nenhuma feature foi extraída.")

if __name__ == "__main__":
    main()