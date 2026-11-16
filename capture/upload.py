#!/usr/bin/env python3
"""
Capturar tráfego OpenVPN (UDP 1194) enquanto simula upload.

Uso:
    sudo python3 wikipedia.py
"""
from datetime import datetime
import argparse
import time
import threading
import os
import random
import logging
from scapy.all import sniff, wrpcap
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

import os
import time
import requests
import random

def simulate_upload(file_path):

    print("[UPLOAD] Enviando arquivo via API pdfrest...")
    upload_url = "https://api.pdfrest.com/upload"
    payload = {}
    files = [('file', ('upload.zip', open('/home/alvaro/Desktop/ic_vpn/upload.zip', 'rb'), 'application/octet-stream'))]
    #headers = {'Api-Key': 'fc31ff8b-9d3c-492f-9e11-d75652c6d608'}
    #headers = {'Api-Key': 'a8b67a82-0019-4be4-b958-a2d465b934cd'}
    #headers = {'Api-Key': '25edf02d-3d03-426b-9725-6ce6bb5c63d2'}
    #headers = {'Api-Key': 'bbbcfa45-ec38-43a7-a52b-de87fda8f971'}
    #headers = {'Api-Key': '9471411d-e78f-4505-8550-d750948e5b0d'}
    #headers = {'Api-Key': '657391ae-2d32-46f0-b24d-bb8026f923c3'}
    #headers = {'Api-Key': '213d8f15-a936-497d-aa0d-5e031a5e602a'}
    #headers = {'Api-Key': '27043ca8-9c60-4675-8be0-618c2fd4c7a9'}
    headers = {'Api-Key': 'cc89f79a-ed16-478a-a2be-0f8005a90c30'}

    with open(file_path, "rb") as f:
        # requests automaticamente gera multipart/form-data
        response = requests.post(upload_url, headers=headers, data=payload, files=files)
    print(response.text)

    print("[UPLOAD] Concluído.\n")


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Variável de controle para interromper a captura
stop_capture_flag = threading.Event()

def capture_packets(interface, filename):
    """Capturar pacotes UDP 1194 (OpenVPN) até que a flag de parada seja ativada."""
    logger.info(f"Iniciando captura na interface {interface}...")

    def stop_filter(packet):
        """Função de filtro de parada do Scapy."""
        return stop_capture_flag.is_set()

    packets = sniff(iface=interface, filter="udp port 1194", stop_filter=stop_filter)
    wrpcap(filename, packets)

def main():
    parser = argparse.ArgumentParser(description='Capturar tráfego OpenVPN durante navegação no Reddit')
    parser.add_argument('--output', '-o', default='reddit.pcap', help='Arquivo de saída .pcap')
    parser.add_argument('--interface', '-i', default='enp0s3', help='Interface de rede')
    args = parser.parse_args()

    if os.geteuid() != 0:
        logger.error("Execute com: sudo python3 capture_reddit.py ...")
        exit(1)
    os.makedirs("capturas", exist_ok=True)
    upload_dir = os.path.realpath("/home/alvaro/Desktop/ic_vpn")
    file_path = os.path.realpath(f"{upload_dir}/upload.zip")
    n = 110
    try:
        for i in range(n):
            print(f"\n{'='*60}")
            print(f"--- Ciclo de captura {i+1}/{n} ---")
            print(f"{'='*60}\n")

            # Gera nome do arquivo com timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join("capturas", f"captura_{timestamp}.pcap")

            # Inicia a captura em thread separada
            capture_thread = threading.Thread(target=capture_packets, args=(args.interface,filename), daemon=True)
            capture_thread.start()

            simulate_upload(file_path)
            
            stop_capture_flag.set()

            # Aguarda finalização da captura
            print("Aguardando finalização da captura...")
            capture_thread.join()

            print(f"\n✓ Ciclo {i+1} concluído com sucesso!")

            # Pequena pausa antes do próximo ciclo
            if i < n - 1:
                print("Preparando próximo ciclo...\n")
                time.sleep(3)
            stop_capture_flag.clear()

    except KeyboardInterrupt:
        print("\n\nCaptura interrompida pelo usuário.")
    except Exception as e:
        print(f"\nErro durante a execução: {str(e)}")
    finally:
        print("Processo finalizado!")

if __name__ == "__main__":
    main()

