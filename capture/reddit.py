#!/usr/bin/env python3
"""
Capturar tráfego OpenVPN (UDP 1194) enquanto simula navegação no Reddit.

Uso:
    sudo python3 capture_reddit.py
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
import random
from time import sleep
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
import pickle

def simulate_reddit(min_time=45, max_time=90):
    # ======================
    # 1) CONFIGURAÇÃO DO DRIVER
    # ======================
    chrome_options = Options()
    '''chrome_options.add_argument("--headless=new")         # modo headless moderno
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--window-size=1920,1080")'''
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-blink-features")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--user-data-dir=/root/selenium-profile")
    

    # IMPORTANTE PARA O SEU TRÁFEGO:
    chrome_options.add_argument("--enable-javascript")
    chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(options=chrome_options, service=service)
    actions = ActionChains(driver)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                // remove webdriver flag
                Object.defineProperty(navigator, 'webdriver', {
                  get: () => undefined
                });

                // mascarar plugins vazios
                Object.defineProperty(navigator, 'plugins', {
                  get: () => [1, 2, 3, 4, 5]
                });

                // mascarar languages
                Object.defineProperty(navigator, 'languages', {
                  get: () => ['pt-BR', 'pt', 'en-US']
                });

                // mascarar chrome.runtime indicando extensão fake
                window.chrome = {
                  runtime: {}
                };

                // reduzir chance de detectar Headless
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                  get: () => 8
                });
            """
        }
    )

    # ======================
    # 2) INÍCIO DA SIMULAÇÃO
    # ======================
    driver.get("https://www.reddit.com")
    sleep(1)
    end_time = time.time() + random.randint(min_time, max_time)

    def human_pause():
        time.sleep(random.uniform(1, 3))

    def long_pause():
        time.sleep(random.uniform(5, 15))

    while time.time() < end_time:
    	prob = random.randint(1,100)
    	print(prob)
    	# 75% de chance de scrollar
    	if prob > 15 and prob <= 85:
    		r = random.randint(1,100)
    		if r < 50:
    			driver.execute_script("window.scrollBy(0, arguments[0]);", random.randint(200, 400))
    		elif r > 50 and r < 80:
    			driver.execute_script("window.scrollBy(0, arguments[0]);", random.randint(600, 1200))
    		else:
    			driver.execute_script("window.scrollBy(0, arguments[0]);", random.randint(-300, -100))
    		human_pause()
    	# 15% de chance de clicar em posts
    	elif prob > 85:
    		# garante que tem posts visíveis
    		driver.execute_script("window.scrollBy(0, 800);")
    		posts = driver.find_elements(By.CSS_SELECTOR, "a.absolute.inset-0")
    		if not posts:
    			print("Nenhum post encontrado")
    			continue
    			# pesos: posts mais perto do topo têm maior peso
    		weights = [1 / (i + 1) for i in range(len(posts))]
    		post = random.choices(posts, weights=weights, k=1)[0]
    		try:
    			driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth', block:'center'});",post)
    			human_pause()
    			# garante que está clicável
    			driver.execute_script("arguments[0].click();", post)
    			long_pause()
    			# scroll dentro do post
    			for _ in range(random.randint(2, 5)):
    				driver.execute_script("window.scrollBy(0, arguments[0]);",random.randint(300, 900))
    				human_pause()
    			# volta ao feed
    			driver.back()
    			sleep(1)
    		except Exception as e:
    			print("Erro ao clicar no post:", e)
    	# 15% de chance de navegar para um subreddit
    	elif prob <= 15:
    		# -------- Navegar para um subreddit --------
    		if random.random() < 0.10:
    			subs = ["r/technology", "r/funny", "r/gaming", "r/worldnews"]
    			try:
    				driver.get(f"https://www.reddit.com/{random.choice(subs)}")
    				sleep(1)
    			except:
    				pass

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
    n = 500
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
            
            simulate_reddit()
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
