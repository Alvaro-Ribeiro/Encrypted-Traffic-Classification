#!/usr/bin/env python3
import pyautogui
import time
import random
import logging
import threading
import os
import argparse
from datetime import datetime
from faker import Faker
from scapy.all import sniff, wrpcap

# =========================================================================
# CONFIGURAÇÕES GERAIS
# =========================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

fake = Faker('pt_BR')

# Evento global de controle de thread para parar o Scapy no momento exato
stop_capture_flag = threading.Event()

# =========================================================================
# FUNÇÕES DE REDE (SCAPY)
# =========================================================================
def capture_packets(interface: str, filename: str) -> bool:
    """
    Roda em uma thread separada capturando pacotes até que a flag seja ativada.
    """
    logger.info(f"[SCAPY] Iniciando captura na interface {interface}...")
    # O sniff fica bloqueado aqui até que a função lambda retorne True
    packets = sniff(iface=interface, stop_filter=lambda x: stop_capture_flag.is_set())
    
    if packets:
        wrpcap(filename, packets)
        logger.info(f"[SCAPY] Captura salva: {filename} ({len(packets)} pacotes)")
    else:
        logger.warning(f"[SCAPY] Nenhum pacote capturado em: {filename}")
        
    return True

# =========================================================================
# FUNÇÕES DE AUTOMAÇÃO HUMANA (HCI)
# =========================================================================
def gerar_mensagem_aleatoria() -> str:
    """Gera textos estocásticos para eliminar o Viés de Dicionário."""
    tipo = random.choices(
        population=['curta', 'media', 'longa'],
        weights=[0.50, 0.35, 0.15], 
        k=1
    )[0]
    
    if tipo == 'curta':
        return " ".join(fake.words(nb=random.randint(1, 2))).capitalize() + "."
    elif tipo == 'media':
        return fake.sentence(nb_words=random.randint(4, 10))
    else:
        return fake.paragraph(nb_sentences=random.randint(2, 4))

def digita_humano(texto: str) -> None:
    """Simula digitação física com distribuição Gaussiana e anomalias de pausa."""
    for char in texto:
        pyautogui.write(char)
        
        atraso = random.gauss(0.1, 0.03)
        atraso = max(0.03, min(atraso, 0.3)) 
        
        if random.random() < 0.03:
            atraso += random.uniform(0.35, 0.85)
            
        time.sleep(atraso)
        
    time.sleep(random.uniform(0.2, 0.6))
    pyautogui.press('enter')

def executar_sessao_chat_core(duracao_minutos: float) -> None:
    """Motor central da simulação de tráfego de mensageria."""
    tempo_final = time.time() + (duracao_minutos * 60)
    
    while time.time() < tempo_final:
        num_mensagens = random.choices([1, 2, 3, 4], weights=[0.40, 0.35, 0.15, 0.10], k=1)[0]
        logger.info(f"--> Iniciando burst de {num_mensagens} mensagem(ns).")
        
        for i in range(num_mensagens):
            mensagem = gerar_mensagem_aleatoria()
            logger.info(f"    Enviando [{i+1}/{num_mensagens}] ({len(mensagem)} chars): {mensagem}")
            digita_humano(mensagem)
            
            if i < num_mensagens - 1:
                time.sleep(random.uniform(0.5, 2.0))
        
        tempo_silencio = random.uniform(6.0, 22.0)
        logger.info(f"Rajada concluída. Ocioso por {tempo_silencio:.1f} segundos...\n")
        time.sleep(tempo_silencio)

# =========================================================================
# ORQUESTRADOR DE LOTE (BATCH PROCESSOR)
# =========================================================================
def orquestrar_lote_capturas(total_capturas: int, duracao_minutos: float, interface: str, output_dir: str) -> None:
    """Gerencia o pipeline integrando Scapy (Thread) e PyAutoGUI (Main Thread)."""
    
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"PREPARAÇÃO: {total_capturas} capturas de {duracao_minutos} minutos na interface '{interface}'.")
    logger.info("=========================================================")
    logger.info("ATENÇÃO: CLIQUE NA CAIXA DE TEXTO DO TELEGRAM WEB AGORA!")
    logger.info("O sistema assume o controle total do teclado em 5 segundos...")
    logger.info("=========================================================")
    time.sleep(5)
    
    for i in range(1, total_capturas + 1):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pcap_file = os.path.join(output_dir, f"captura_chat_{timestamp}.pcap")
        
        logger.info(f"\n[+] INICIANDO CICLO {i}/{total_capturas} -> Arquivo: {pcap_file}")
        
        # 1. Inicia o Scapy
        cap_thread = threading.Thread(target=capture_packets, args=(interface, pcap_file), daemon=True)
        cap_thread.start()
        
        # 2. Roda a automação do Chat
        executar_sessao_chat_core(duracao_minutos)
        
        # 3. Para o Scapy IMEDIATAMENTE (Tráfego do PCAP encerra aqui)
        stop_capture_flag.set()
        cap_thread.join()
        stop_capture_flag.clear()
        
        logger.info(f"[-] CICLO {i} FINALIZADO. Executando Hard-Reset do ambiente...")
        
        # =========================================================
        # 4. HARD-RESET (Limpeza fora do escopo da captura de rede)
        # =========================================================
        
        # A) Envia a string de limpeza para o Bot acionar a API e deletar tudo
        # A) Força a barra pelo código universal 'divide' e depois escreve o resto
        pyautogui.press('divide') 
        pyautogui.write('limpar')
        pyautogui.press('enter')
        
        # Espera o bot processar a deleção das mensagens
        time.sleep(3) 
        
        # B) Força o recarregamento do navegador (Ctrl+R / F5) para liberar a RAM
        # Use 'f5' no Windows/Linux, ou hotkey('ctrl', 'r') 
        pyautogui.press('f5')
        
        logger.info("Aguardando para a página web recarregar completamente...")
        time.sleep(5)
        time.sleep(1)
    
    '''for i in range(1, total_capturas + 1):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pcap_file = os.path.join(output_dir, f"captura_chat_{timestamp}.pcap")
        
        logger.info(f"\n[+] INICIANDO CICLO {i}/{total_capturas} -> Arquivo: {pcap_file}")
        
        # 1. Inicia o Scapy em background (Thread daemon)
        cap_thread = threading.Thread(
            target=capture_packets,
            args=(interface, pcap_file),
            daemon=True
        )
        cap_thread.start()
        
        # 2. Roda a automação do Chat (bloqueia o script pelo tempo definido)
        executar_sessao_chat_core(duracao_minutos)
        
        # 3. Para o Scapy com segurança
        stop_capture_flag.set()
        cap_thread.join()
        stop_capture_flag.clear() # Limpa a flag para o próximo ciclo
        
        logger.info(f"[-] CICLO {i} FINALIZADO.")
        time.sleep(2) # Micro-pausa antes do próximo ciclo
        
    logger.info("\n✅ PIPELINE CONCLUÍDO! Todas as capturas de Chat foram salvas.")'''


# =========================================================================
# ENTRY POINT
# =========================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script de Geração e Captura de Tráfego de Chat (TCC)")
    parser.add_argument("-i", "--interface", default="enp0s3", help="Interface de rede para capturar (ex: tun0, enp0s3)")
    parser.add_argument("-o", "--output", default="capturas_chat", help="Pasta para salvar os arquivos .pcap")
    parser.add_argument("-c", "--capturas", type=int, default=250, help="Número total de ciclos de captura a realizar")
    parser.add_argument("-t", "--tempo", type=float, default=5, help="Duração de cada captura em minutos")
    
    args = parser.parse_args()

    # Bloqueio de segurança: Scapy exige root para rodar o sniff
    if os.geteuid() != 0:
        logger.error("Este script utiliza o Scapy e precisa ser executado como superusuário (root/sudo).")
        exit(1)

    orquestrar_lote_capturas(
        total_capturas=args.capturas,
        duracao_minutos=args.tempo,
        interface=args.interface,
        output_dir=args.output
    )
