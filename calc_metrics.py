# Uso: python calc_metrics.py --pcap captura_netflix.pcap --client-ip 10.0.2.15 --service Netflix --category Streaming
import os
import argparse
import math
import numpy as np
import pandas as pd
from scapy.all import PcapReader, IP
from scipy.stats import entropy
from datetime import datetime
import warnings

# Suprimir avisos estatísticos para arrays vazios em ambiente de produção
warnings.filterwarnings("ignore", category=RuntimeWarning)

# ============================================================
# Funções Auxiliares (Matemática e Estatística)
# ============================================================

def calc_entropy(values, bins=10):
    """Calcula a entropia de uma lista de valores contínuos."""
    if len(values) == 0:
        return 0.0
    hist, _ = np.histogram(values, bins=bins, density=True)
    hist = hist[hist > 0]
    return float(entropy(hist))

def autocorr(x, lag=1):
    """Autocorrelação simples em um determinado lag. Retorna 0.0 em caso de erro/NaN."""
    x = np.array(x)
    if len(x) <= lag:
        return 0.0
    x = x - np.mean(x)
    denom = np.sum(x ** 2)
    if denom == 0:
        return 0.0
    val = np.sum(x[:-lag] * x[lag:]) / denom
    return 0.0 if np.isnan(val) else float(val)

def find_agnostic_keep_alive_threshold(packet_sizes):
    """
    Determina o limiar de tamanho de pacote para keep-alives de forma agnóstica
    analisando a distribuição de tamanho de pacote (método do vale).
    """
    if not packet_sizes:
        return 100

    min_size = min(packet_sizes)
    max_size = max(packet_sizes)

    if min_size == max_size:
        return min_size

    bins = range(min_size, max_size + 2)
    counts, _ = np.histogram(packet_sizes, bins=bins)

    window_size = 5
    smoothed_counts = np.convolve(counts, np.ones(window_size)/window_size, mode='valid')
    smoothed_bins = np.array(bins[:-window_size]) + (window_size // 2)

    search_limit = min(len(smoothed_counts), max(1, 150 - min_size))
    if search_limit <= 0:
        return 100 

    first_peak_index = np.argmax(smoothed_counts[:search_limit])
    gradient = np.diff(smoothed_counts)

    for i in range(first_peak_index, len(gradient) - 1):
        if gradient[i] < 0 and gradient[i+1] >= 0:
            threshold_index = i + 1
            return int(smoothed_bins[threshold_index])

    return 100

# ============================================================
# Funções de Domínio (Bursts e Tempo)
# ============================================================

def compute_bursts(df, window_duration, threshold=0.1):
    """Detecta bursts por IAT e calcula as métricas correspondentes."""
    empty_burst_metrics = {
        "burst_count": 0, "burst_rate": 0.0, "avg_packets_per_burst": 0.0,
        "avg_bytes_per_burst": 0.0, "burst_size_std": 0.0, "burst_duration_mean": 0.0,
        "mean_upstream_burst_gap": 0.0, "mean_downstream_burst_gap": 0.0,
        "burst_energy_ratio": 0.0, "burst_iat_std": 0.0
    }

    if df is None or len(df) < 2:
        return empty_burst_metrics

    timestamps = df["timestamp"].astype(float).values
    sizes = df["size"].astype(float).values
    directions = df["direction"].values

    iat = np.diff(timestamps)
    iat = np.insert(iat, 0, np.inf)

    bursts = []
    in_burst = False
    burst_packet_indices = []

    for i in range(1, len(timestamps)):
        if iat[i] < threshold:
            if not in_burst:
                in_burst = True
                burst_packet_indices = [i - 1, i]
            else:
                burst_packet_indices.append(i)
        else:
            if in_burst:
                pkt_idxs = burst_packet_indices
                start_time = float(timestamps[pkt_idxs[0]])
                end_time = float(timestamps[pkt_idxs[-1]])
                duration = max(0.0, end_time - start_time)
                bytes_sum = float(np.sum(sizes[pkt_idxs]))
                
                dir_values = directions[pkt_idxs]
                out_count = np.sum(dir_values == "outgoing")
                in_count = np.sum(dir_values == "incoming")
                burst_dir = "outgoing" if out_count >= in_count else "incoming"

                bursts.append({
                    "packets": len(pkt_idxs), "bytes": bytes_sum,
                    "start_time": start_time, "end_time": end_time,
                    "duration": duration, "direction": burst_dir
                })
                in_burst = False
                burst_packet_indices = []

    if in_burst and burst_packet_indices:
        pkt_idxs = burst_packet_indices
        start_time = float(timestamps[pkt_idxs[0]])
        end_time = float(timestamps[pkt_idxs[-1]])
        duration = max(0.0, end_time - start_time)
        bytes_sum = float(np.sum(sizes[pkt_idxs]))
        
        dir_values = directions[pkt_idxs]
        out_count = np.sum(dir_values == "outgoing")
        in_count = np.sum(dir_values == "incoming")
        burst_dir = "outgoing" if out_count >= in_count else "incoming"

        bursts.append({
            "packets": len(pkt_idxs), "bytes": bytes_sum,
            "start_time": start_time, "end_time": end_time,
            "duration": duration, "direction": burst_dir
        })

    if len(bursts) == 0:
        return empty_burst_metrics

    burst_df = pd.DataFrame(bursts)
    
    burst_count = len(burst_df)
    burst_rate = burst_count / window_duration if window_duration > 0 else 0.0
    
    total_burst_bytes = burst_df["bytes"].sum()
    if total_burst_bytes > 0:
        top_k = max(1, int(math.ceil(0.2 * len(burst_df))))
        burst_energy_ratio = float(burst_df.nlargest(top_k, "bytes")["bytes"].sum() / total_burst_bytes)
    else:
        burst_energy_ratio = 0.0

    burst_start_times = burst_df["start_time"].values
    burst_iat_std = float(np.std(np.diff(burst_start_times), ddof=0)) if len(burst_start_times) > 1 else 0.0

    up_gaps, down_gaps = [], []
    last_up_end, last_down_end = None, None

    for _, row in burst_df.iterrows():
        start, end, d = float(row["start_time"]), float(row["end_time"]), row["direction"]
        if d == "outgoing":
            if last_up_end is not None and (start - last_up_end) >= 0:
                up_gaps.append(start - last_up_end)
            last_up_end = end
        else:
            if last_down_end is not None and (start - last_down_end) >= 0:
                down_gaps.append(start - last_down_end)
            last_down_end = end

    return {
        "burst_count": int(burst_count),
        "burst_rate": float(burst_rate),
        "avg_packets_per_burst": float(burst_df["packets"].mean()),
        "avg_bytes_per_burst": float(burst_df["bytes"].mean()),
        "burst_size_std": float(burst_df["bytes"].std(ddof=0)) if burst_count > 1 else 0.0,
        "burst_duration_mean": float(burst_df["duration"].mean()),
        "mean_upstream_burst_gap": float(np.mean(up_gaps)) if up_gaps else 0.0,
        "mean_downstream_burst_gap": float(np.mean(down_gaps)) if down_gaps else 0.0,
        "burst_energy_ratio": float(burst_energy_ratio),
        "burst_iat_std": float(burst_iat_std)
    }

def compute_temporal_distribution(df, window_duration):
    """Divide a janela em 4 quartis de tempo e mede distribuição de bytes."""
    byte_quartiles = [0, 0, 0, 0]
    packet_quartiles = [0, 0, 0, 0]
    
    if window_duration <= 0 or len(df) == 0:
        return {
            "byte_quartile_1": 0.0, "byte_quartile_2": 0.0, "byte_quartile_3": 0.0, "byte_quartile_4": 0.0,
            "early_vs_late_ratio": 0.0, "max_rate_quartile": 1, "std_rate_quartiles": 0.0,
            "packet_quartile_1": 0.0, "packet_quartile_2": 0.0, "packet_quartile_3": 0.0, "packet_quartile_4": 0.0,
        }

    start_t = df['timestamp'].iloc[0]
    
    # Vetorização para ganho de performance
    df_temp = df.copy()
    df_temp['q_idx'] = ((df_temp['timestamp'] - start_t) / window_duration * 4).astype(int)
    df_temp.loc[df_temp['q_idx'] == 4, 'q_idx'] = 3
    
    b_totals = df_temp.groupby('q_idx')['size'].sum().to_dict()
    p_totals = df_temp.groupby('q_idx').size().to_dict()
    
    for i in range(4):
        byte_quartiles[i] = b_totals.get(i, 0)
        packet_quartiles[i] = p_totals.get(i, 0)

    b_total = sum(byte_quartiles)
    p_total = sum(packet_quartiles)
    
    byte_quartiles = [q / b_total if b_total > 0 else 0 for q in byte_quartiles]
    packet_quartiles = [q / p_total if p_total > 0 else 0 for q in packet_quartiles]

    early_bytes = byte_quartiles[0] + byte_quartiles[1]
    late_bytes = byte_quartiles[2] + byte_quartiles[3]
    early_vs_late_ratio = early_bytes / late_bytes if late_bytes > 0 else 0.0

    return {
        "byte_quartile_1": byte_quartiles[0],
        "byte_quartile_2": byte_quartiles[1],
        "byte_quartile_3": byte_quartiles[2],
        "byte_quartile_4": byte_quartiles[3],
        "early_vs_late_ratio": float(early_vs_late_ratio),
        "max_rate_quartile": int(np.argmax(byte_quartiles) + 1),
        "std_rate_quartiles": float(np.std(byte_quartiles)),
        "packet_quartile_1": packet_quartiles[0],
        "packet_quartile_2": packet_quartiles[1],
        "packet_quartile_3": packet_quartiles[2],
        "packet_quartile_4": packet_quartiles[3],
    }

# ============================================================
# Core Pipeline
# ============================================================

def process_pcap(pcap_file, client_ip, service, category, vpn_type="OpenVPN"):
    """Lê o arquivo pcap em streaming e calcula todas as features de rede."""
    session_id = os.path.basename(pcap_file).replace(".pcap", "")
    packets_data = []
    
    # 1. Leitura Otimizada (Streaming)
    try:
        with PcapReader(pcap_file) as pcap:
            for pkt in pcap:
                if IP in pkt:
                    packets_data.append({
                        "timestamp": float(pkt.time),
                        "size": len(pkt),
                        "direction": "outgoing" if pkt[IP].src == client_ip else "incoming"
                    })
    except Exception as e:
        print(f"Erro ao ler {pcap_file}: {e}")
        return None

    if not packets_data:
        return None

    df_raw = pd.DataFrame(packets_data)
    
    # 2. Limiar Dinâmico e Filtragem
    keep_alive_threshold = find_agnostic_keep_alive_threshold(df_raw["size"].tolist())
    df = df_raw[df_raw["size"] >= keep_alive_threshold].copy()
    
    if len(df) < 2:
        return None

    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    df["iat"] = df["timestamp"].diff().astype(float)
    iat_values = df["iat"].dropna().values

    # 3. Metadados de Tempo
    window_start = df["timestamp"].iloc[0]
    window_end = df["timestamp"].iloc[-1]
    window_duration = float(window_end - window_start)
    capture_date = datetime.fromtimestamp(window_start).strftime("%Y-%m-%d %H:%M:%S")

    # 4. Cálculo de Atividade (Baseado na Documentação Teórica)
    if len(iat_values) > 0 and window_duration > 0:
        # Pega o 95º percentil como limiar dinâmico de inatividade
        dynamic_iat_threshold = np.percentile(iat_values, 95)
        duration_active_s = float(iat_values[iat_values <= dynamic_iat_threshold].sum())
        active_ratio = duration_active_s / window_duration
    else:
        duration_active_s = 0.0
        active_ratio = 0.0

    # 5. Volumetria Básica
    total_packets = len(df)
    total_bytes = df["size"].sum()
    sent_df = df[df["direction"] == "outgoing"]
    recv_df = df[df["direction"] == "incoming"]

    packets_sent = len(sent_df)
    packets_recv = len(recv_df)
    bytes_sent = sent_df["size"].sum()
    bytes_recv = recv_df["size"].sum()

    packet_rate = total_packets / window_duration if window_duration > 0 else 0.0
    byte_rate = total_bytes / window_duration if window_duration > 0 else 0.0
    up_down_packet_ratio = packets_sent / packets_recv if packets_recv > 0 else packets_sent
    up_down_byte_ratio = bytes_sent / bytes_recv if bytes_recv > 0 else bytes_sent

    # 6. Correção de Mudanças de Direção (Evita falso positivo da primeira linha nula)
    direction_changes = int((df["direction"].shift().dropna() != df["direction"].iloc[1:]).sum())
    direction_changes_rate = direction_changes / window_duration if window_duration > 0 else 0.0

    # 7. Retorno consolidado
    row = {
        "session_id": session_id,
        "capture_date": capture_date,
        "window_start_ts": window_start,
        "window_end_ts": window_end,
        "window_duration_s": window_duration,
        "vpn_type": vpn_type,
        "client_vm": "client_vm",
        "server_vm": "server_vm",
        "total_packets": int(total_packets),
        "total_bytes": int(total_bytes),
        "packets_sent": int(packets_sent),
        "packets_recv": int(packets_recv),
        "bytes_sent": int(bytes_sent),
        "bytes_recv": int(bytes_recv),
        "packet_rate": float(packet_rate),
        "byte_rate": float(byte_rate),
        "up_down_packet_ratio": float(up_down_packet_ratio),
        "up_down_byte_ratio": float(up_down_byte_ratio),
        "packet_size_mean": float(df["size"].mean()),
        "packet_size_median": float(df["size"].median()),
        "packet_size_std": float(df["size"].std(ddof=0)) if len(df) > 1 else 0.0,
        "packet_size_mean_sent": float(sent_df["size"].mean()) if packets_sent > 0 else 0.0,
        "packet_size_std_sent": float(sent_df["size"].std(ddof=0)) if packets_sent > 1 else 0.0,
        "packet_size_mean_recv": float(recv_df["size"].mean()) if packets_recv > 0 else 0.0,
        "packet_size_std_recv": float(recv_df["size"].std(ddof=0)) if packets_recv > 1 else 0.0,
        "iat_mean": float(np.mean(iat_values)) if len(iat_values) > 0 else 0.0,
        "iat_median": float(np.median(iat_values)) if len(iat_values) > 0 else 0.0,
        "iat_std": float(np.std(iat_values, ddof=0)) if len(iat_values) > 1 else 0.0,
        "autocorr_iat": autocorr(iat_values),
        "autocorr_size": autocorr(df["size"].values),
        "duration_active_s": duration_active_s,
        "active_ratio": active_ratio,
        "entropy_packet": calc_entropy(df["size"].values),
        "entropy_iat": calc_entropy(iat_values),
        "direction_changes": direction_changes,
        "direction_changes_rate": direction_changes_rate,
        **compute_bursts(df, window_duration),
        **compute_temporal_distribution(df, window_duration),
        "service": service,
        "category": category
    }

    return row

# ============================================================
# Interface CLI
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Processa .pcap e gera features para o dataset")
    parser.add_argument("--pcap", required=True, help="Arquivo .pcap de entrada")
    parser.add_argument("--client-ip", required=True, help="Endereço IP da máquina cliente")
    parser.add_argument("--service", required=True, help="Rótulo (Serviço)")
    parser.add_argument("--category", required=True, help="Rótulo (Categoria)")
    args = parser.parse_args()

    out_file = "dataset.csv"
    session_id = os.path.basename(args.pcap).replace(".pcap", "")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando processamento: {session_id}")

    # 1. Verificação de Duplicatas Ultrarrápida
    file_exists = os.path.exists(out_file)
    if file_exists:
        try:
            # Lê apenas a coluna 'session_id' para não estourar a memória
            existing_sessions = pd.read_csv(out_file, usecols=["session_id"])["session_id"].astype(str).values
            if session_id in existing_sessions:
                print(f" -> Session_id '{session_id}' já existe no CSV. Processo ignorado.")
                exit(0)
        except Exception as e:
            print(f" -> Aviso ao ler CSV existente: {e}")

    # 2. Processamento do Pcap
    row = process_pcap(args.pcap, args.client_ip, args.service, args.category)

    if row is None:
        print(f" -> Arquivo '{session_id}' ignorado: Tráfego insuficiente ou vazio após filtragem.")
        exit(1)

    # 3. Escrita em Append Mode (O(1) complexidade de tempo)
    df_out = pd.DataFrame([row])
    df_out.to_csv(out_file, mode='a', header=not file_exists, index=False)
    
    print(f" -> Sucesso! Dados de '{session_id}' salvos em {out_file}.")