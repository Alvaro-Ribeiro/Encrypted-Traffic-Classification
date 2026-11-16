from datetime import datetime
import argparse
import time
import threading
import os
import random
import logging
from scapy.all import sniff, wrpcap
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from time import sleep

def simulate_twitch(interface,filename):
	options=Options()
	options.add_argument("--no-sandbox")
	service = Service('/usr/bin/chromedriver')
	driver = webdriver.Chrome(service=service, options=options)
	try:
		capture_thread = threading.Thread(target=capture_packets, args=(interface,filename), daemon=True)
		driver.get("https://www.twitch.tv/leekbeats")
		sleep(3)
		capture_thread.start()
		sleep(60)
		stop_capture_flag.set()
		capture_thread.join()
		stop_capture_flag.clear()
	finally:
		driver.quit()

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

    print("começou a captura")
    packets = sniff(iface=interface, filter="udp port 1194", stop_filter=stop_filter)
    print("terminou a captura")
    wrpcap(filename, packets)

def main():
    interface = 'enp0s3'

    if os.geteuid() != 0:
        logger.error("Execute com: sudo python3 capture_reddit.py ...")
        exit(1)
    os.makedirs("capturas", exist_ok=True)
    n = 500
    try:
        for i in range(n):
            print(f"\n{'='*60}")
            print(f"--- Ciclo de captura {i+1}/{n} ---")
            print(f"{'='*60}\n")

            # Gera nome do arquivo com timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join("capturas", f"captura_{timestamp}.pcap")
            
            simulate_twitch(interface, filename)

            # Pequena pausa antes do próximo ciclo
            if i < n - 1:
                print("Preparando próximo ciclo...\n")
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nCaptura interrompida pelo usuário.")
    except Exception as e:
        print(f"\nErro durante a execução: {str(e)}")
    finally:
        print("Processo finalizado!")

main()

