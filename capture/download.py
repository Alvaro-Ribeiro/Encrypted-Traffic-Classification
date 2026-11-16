#!/usr/bin/env python3
import threading
import time
import os
from datetime import datetime
import argparse
import logging
import random
import requests
from scapy.all import sniff, wrpcap

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

stop_capture_flag = threading.Event()

# ============================================================
#  LISTA DE TAMANHOS DE DOWNLOAD (OPÇÃO 2)
# ============================================================
DOWNLOAD_SIZES_MB = [10, 20, 50, 75, 100, 150]


def get_random_download_url():
    size_mb = random.choice(DOWNLOAD_SIZES_MB)
    size_bytes = size_mb * 1024 * 1024
    print(f"[INFO] Selecionado download de {size_mb} MB")
    return f"https://speed.cloudflare.com/__down?bytes={size_bytes}"


# ============================================================
#  SIMULAÇÃO REAL DE DOWNLOAD (TRÁFEGO REAL)
# ============================================================
def simulate_real_download(url, chunk_size=4096):
    """
    Executa um download real e imprime progresso/velocidade.
    """
    print(f"[DOWNLOAD] Iniciando download real: {url}")

    try:
        r = requests.get(url, stream=True, timeout=10)

        total = 0
        start = time.time()

        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:
                total += len(chunk)
                elapsed = time.time() - start
                speed_kb = (total / 1024) / elapsed if elapsed > 0 else 0

                print(f"\r[DOWNLOAD] Recebidos: {total/1024:.1f} KB | Velocidade: {speed_kb:.1f} KB/s", end="")

        print("\n[DOWNLOAD] Concluído!")
        return True

    except Exception as e:
        print(f"[DOWNLOAD] ERRO no download: {e}")
        return False


# ============================================================
#  CAPTURA (com validação)
# ============================================================
def capture_packets(interface, filename):
    """Captura pacotes UDP porta 1194 até o stop flag ser ativado."""

    logger.info(f"[CAPTURA] Iniciando captura em {interface}...")

    def stop_filter(pkt):
        return stop_capture_flag.is_set()

    packets = sniff(
        iface=interface,
        filter="udp port 1194",
        stop_filter=stop_filter
    )

    # salvar somente se houver pacotes
    if len(packets) == 0:
        print("[CAPTURA] Nenhum pacote capturado. Arquivo NÃO será salvo.")
        return False

    wrpcap(filename, packets)
    print(f"[CAPTURA] Captura salva: {filename} ({len(packets)} pacotes)")
    return True


# ============================================================
#  MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--interface", default="enp0s3")
    parser.add_argument("-o", "--output", default="capturas")
    args = parser.parse_args()

    if os.geteuid() != 0:
        print("Execute com sudo.")
        exit(1)

    os.makedirs(args.output, exist_ok=True)

    ciclos = 3

    for i in range(ciclos):
        print(f"\n=== CICLO {i+1}/{ciclos} ===")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pcap_file = os.path.join(args.output, f"captura_{timestamp}.pcap")

        # URL aleatória com tamanho pré-definido
        url = get_random_download_url()

        # iniciar captura
        cap_thread = threading.Thread(
            target=capture_packets,
            args=(args.interface, pcap_file),
            daemon=True
        )

        cap_thread.start()

        # simulação REAL de download
        download_ok = simulate_real_download(url=url)

        # parar captura
        stop_capture_flag.set()
        cap_thread.join()
        stop_capture_flag.clear()

        if not download_ok:
            print("[CICLO] Download falhou → ciclo ignorado.")
        else:
            print(f"[OK] Ciclo {i+1} concluído!\n")

    print("=== FINALIZADO ===")


if __name__ == "__main__":
    main()

