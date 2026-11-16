# Classificação Comportamental de Tráfego de Rede Criptografado (OpenVPN) via Aprendizado de Máquina

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Protocolo](https://img.shields.io/badge/VPN-OpenVPN%20(UDP%201194)-green)
![ML](https://img.shields.io/badge/ML-CatBoost%20%7C%20Random%20Forest-orange)
![Colab](https://img.shields.io/badge/Notebook-Google%20Colab-F9AB00?logo=googlecolab&logoColor=white)

Repositório oficial do Trabalho de Conclusão de Curso (TCC) em **Engenharia de Computação** pelo **CEFET/RJ — *Campus* Petrópolis**, dedicado à identificação de aplicações em fluxos de rede encapsulados por túneis criptográficos **OpenVPN (AES-256-GCM / UDP 1194)** utilizando exclusivamente **análise estatística de canal lateral (*Side-Channel Analysis*)** livre de *Data Leakage*.

---

## 📌 Visão Geral e Motivação

Com a adoção massiva de túneis VPN e cifras ponta a ponta, técnicas tradicionais de classificação de tráfego baseadas em mapeamento de portas da camada de transporte (IANA) e **Inspeção Profunda de Pacotes (DPI)** tornaram-se ineficazes, pois o encapsulamento oculta cabeçalhos internos e transforma a carga útil (*payload*) em sequências de alta entropia.

Este projeto demonstra que, embora a criptografia proteja o conteúdo das mensagens, **propriedades físicas externas sobrevivem ao tunelamento**:
1. **Dimensão Espacial:** O comprimento dos datagramas cifrados mantém relação determinística com o pacote original e com o limite de MTU da rede (~1.500 bytes).
2. **Dimensão Temporal:** Os instantes de chegada e o **Tempo de Interchegada (*Packet Inter-Arrival Time* — IAT)** preservam a cadência e a geometria de rajadas (*bursts*) de cada protocolo.

---

## 🏗️ Arquitetura do Pipeline (4 Etapas)

1. **Coleta Automatizada (`capture/`):** Suítes dedicadas em Python geram tráfego orgânico para **6 classes canônicas** sob túnel OpenVPN e interceptam os pacotes pós-cifragem na interface física externa utilizando `Scapy` com filtro **BPF (`udp port 1194`)**.
2. **Extração Estatística L4 (`run.py`, `calc_metrics.py`, `clean_csv.py`):** Executado na raiz do projeto, o orquestrador `run.py` varre automaticamente `./pcaps/`, aciona o extrator `calc_metrics.py` em paralelo para vetorizar cada `.pcap` em 59 colunas brutas e executa o `clean_csv.py` para sanear metadados residuais de paralelismo.
3. **Filtragem Anti-Vazamento (`notebooks/Classification.ipynb`):** No Google Colab, o notebook descarta **17 colunas** (metadados e grandezas extensivas dependentes da duração da coleta) e retém estritamente **40 atributos estatísticos intensivos** padronizados via `StandardScaler`.
4. **Modelagem e Avaliação *Line-Rate* (`notebooks/Classification.ipynb`):** Otimização via `GridSearchCV` com validação cruzada estratificada ($k=5$, métrica `F1-Score Macro`) comparando **CatBoost**, **Random Forest**, **LightGBM**, **MLP** e **SVM**.

---

## 📂 Estrutura do Repositório

```text
├── README.md                          # Documentação principal
├── requirements.txt                   # Dependências Python para coleta e extração
├── run-instructions.txt               # Comandos de preparação do ambiente antes da captura
├── .gitignore                         # Regras de exclusão de arquivos brutos e temporários
│
├── calc_metrics.py                    # Motor de cálculo estatístico por .pcap
├── clean_csv.py                       # Limpeza de metadados extras do processamento paralelo
├── run.py                             # Orquestrador na raiz: busca ./pcaps e gera o CSV final
│
├── capture/                           # Automação de tráfego e captura (.pcap)
│   ├── youtube.py                     # Vídeo sob demanda DASH (Selenium + CDP anti-bot)
│   ├── twitch.py                      # Transmissão ao vivo em regime Drip-Feed
│   ├── reddit.py                      # Navegação web assíncrona probabilística
│   ├── telegram.py                    # Mensageria com digitação Gaussiana (PyAutoGUI + Faker)
│   ├── download.py                    # Saturação downstream (Cloudflare Speedtest)
│   └── upload.py                      # Saturação upstream (API multipart/form-data)
│
├── pcaps/                             # Capturas organizadas por <serviço>-<categoria>
│   ├── youtube-streaming/
│   ├── twitch-livestreaming/
│   ├── reddit-web/
│   ├── telegram-chatting/
│   ├── cloudflare-download/
│   └── pdfrest-upload/
│
└── notebooks/                         # Pipeline de IA e visualização de resultados
    └── Classification.ipynb           # Notebook completo para Google Colab
```

---

## 🛠️ Guia Passo a Passo: Como Realizar as Capturas de Tráfego

Para reproduzir a coleta de dados em um ambiente controlado sem contaminar as amostras com pacotes em texto claro ou falhas de automação gráfica, siga rigorosamente as etapas abaixo.

### 1. Pré-requisitos de Infraestrutura
* **Sistema Operacional:** Ambiente Linux com servidor gráfico X11 (testado em **Ubuntu 22.04 LTS**).
* **Túnel VPN Ativo:** Cliente **OpenVPN** conectado a um servidor VPN operando sobre **UDP porta 1194** (criando a interface virtual `tun0` sobre a interface física externa, como `enp0s3`).
* **Navegador Web:** Google Chrome / Chromium instalado (necessário para as automações baseadas em `Selenium` e `PyAutoGUI`).

### 2. Instalação das Bibliotecas Necessárias
Clone o repositório, crie um ambiente virtual (opcional, mas recomendado) e instale todas as dependências listadas em `requirements.txt`:

```bash
git clone [https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git](https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git)
cd SEU-REPOSITORIO

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Comandos Obrigatórios Pré-Captura (`run-instructions.txt`)
> ⚠️ **ATENÇÃO — LEITURA E EXECUÇÃO OBRIGATÓRIA ANTES DE RODAR QUALQUER CAPTURA:**
> Como a biblioteca `Scapy` exige execução como superusuário (`sudo`) para abrir *raw sockets* na interface de rede, o usuário `root` precisa ter permissão explícita para acessar o servidor gráfico (X11) e o subsistema de áudio/mídia (`PipeWire`/`audio`) da sessão atual — caso contrário, o `Selenium`, o `PyAutoGUI` e a reprodução de vídeo (YouTube/Twitch) serão bloqueados pelo sistema operacional.

Execute exatamente os comandos documentados em **`run-instructions.txt`** antes de iniciar as coletas:

```bash
# Comandos de permissões
sudo usermod -aG pipewire root
sudo usermod -aG audio root
xhost +SI:localuser:root
```

* **`usermod -aG pipewire root` e `audio`:** Permitem que navegadores iniciados sob `sudo` reproduzam fluxos de áudio e vídeo normalmente, garantindo o comportamento real de *buffering* (DASH/Livestreaming).
* **`xhost +SI:localuser:root`:** Autoriza o usuário `root` a abrir janelas gráficas e simular eventos de teclado/mouse (`Selenium` e `PyAutoGUI`) no display do usuário local.

### 4. Executando os Scripts de Captura e Organizando os `.pcap`
Com o túnel OpenVPN ativo e as permissões aplicadas, acesse a pasta `capture/` e execute o script correspondente ao serviço desejado com `sudo`:

```bash
cd capture

# Rodar script de captura desejado (Exemplos):
sudo python3 telegram.py
sudo python3 youtube.py
sudo python3 twitch.py
sudo python3 reddit.py
sudo python3 download.py
sudo python3 upload.py
```

**Regra de Organização das Pastas (`./pcaps`):**
Todos os arquivos `.pcap` gerados devem ser armazenados dentro do diretório `pcaps/` na raiz do projeto, seguindo obrigatoriamente a convenção **`<nome_servico>-<nome_categoria>`**, pois o script `run.py` utiliza o nome de cada subpasta para rotular automaticamente as instâncias:

| Pasta em `./pcaps/` | Serviço Emulado | Classe Alvo no Modelo | Comportamento na Camada de Transporte |
| :--- | :--- | :--- | :--- |
| `pcaps/cloudflare-download/` | Cloudflare Speedtest | `Download` | Saturação contínua *downstream* (~1.514 B) |
| `pcaps/pdfrest-upload/` | API PDFRest | `Upload` | Saturação contínua *upstream* (~1.392 B) |
| `pcaps/youtube-streaming/` | YouTube | `Streaming` (VoD) | Rajadas binárias ON-OFF (protocolo DASH) |
| `pcaps/twitch-livestreaming/` | Twitch | `Livestreaming` | Gotejamento contínuo de baixa latência (*Drip-Feed*) |
| `pcaps/reddit-web/` | Reddit | `WEB` | Rajadas curtas assíncronas e leitura intermitente |
| `pcaps/telegram-chatting/` | Telegram Web | `Chatting` | Micro-pacotes esparsos com pausas cognitivas humanas |

---

## ⚙️ Extração de Atributos e Geração do Dataset (`run.py`)

Os scripts de extração ficam posicionados na **raiz do repositório**, pois o orquestrador busca automaticamente pela pasta `./pcaps` no diretório local:

* **`calc_metrics.py`:** Realiza a leitura incremental (*streaming*) de cada `.pcap` via `PcapReader` (baixo consumo de RAM), separa o fluxo bidirecional (`sent` / `recv`) e computa **59 colunas brutas** distribuídas em cinco grupos: *Tamanho de Pacotes*, *Tempo de Interchegada (IAT)*, *Taxas de Fluxo*, *Dinâmica de Rajadas ($\tau = 100\text{ ms}$)* e *Quartis Temporais*.
* **`clean_csv.py`:** Remove metadados extras e artefatos de cabeçalho/indexação gerados durante a execução paralela do `calc_metrics.py`.
* **`run.py`:** Script principal que automatiza toda a esteira local — varre recursivamente `./pcaps/<servico>-<categoria>/`, invoca `calc_metrics.py` em paralelo, consolida os registros e aciona `clean_csv.py` para gerar o `.csv` final limpo.

Na raiz do projeto, execute apenas:

```bash
python3 run.py
```

---

## 🧠 Treinamento e Classificação no Google Colab (`Classification.ipynb`)

Com o arquivo `.csv` consolidado gerado pelo `run.py`, todo o pipeline de Inteligência Artificial é executado na nuvem por meio do notebook **`notebooks/Classification.ipynb`**:

1. Acesse o [Google Colab](https://colab.research.google.com/) e faça o *upload* de `notebooks/Classification.ipynb`.
2. Faça o *upload* do arquivo `.csv` gerado na etapa anterior para o ambiente do Colab (ou monte seu Google Drive).
3. Execute todas as células sequencialmente (`Runtime -> Run all`).

### O que o `Classification.ipynb` executa:
* **Filtragem Anti-Vazamento (*Anti-Data Leakage*):** De um total de **59 colunas**, expurga **17 variáveis** (6 metadados de sessão/VM e 11 contadores extensivos dependentes do tempo, como `total_bytes`, `total_packets` e `window_duration_s`) além das 2 colunas de rótulo alvo ($Y$), isolando **40 preditores puramente intensivos ($X$)**.
* **Pré-processamento:** Tratamento de `NaN`/infinitos, codificação discreta das 6 classes (`LabelEncoder`) e padronização Z-Score (`StandardScaler`).
* **Validação Experimental:** Particionamento estratificado **70% Treino / 30% Teste Cego**, com otimização de hiperparâmetros via `GridSearchCV` e validação cruzada estratificada de 5 dobras (`k=5`) guiada pela métrica **`F1-Score Macro`**.

---

## 📊 Resultados de Referência (Benchmark do Estudo)

Avaliação experimental conduzida sobre **6.114 capturas** (4.279 treino / 1.835 teste cego isolado):

| Modelo | Tempo de Treino (s) | Latência ($\mu$s/fluxo) | Acurácia (%) | F1-Score Macro |
| :--- | :---: | :---: | :---: | :---: |
| **CatBoost (Ótimo *Line-Rate*)** | 3,40 | **3,90** | **99,95%** | **0,9994** |
| **Random Forest** | 1,44 | 11,86 | **99,95%** | **0,9994** |
| **LightGBM** | 1,40 | 22,76 | 99,84% | 0,9984 |
| **MLP (Rede Neural)** | 1,57 | 3,76 | 99,78% | 0,9978 |
| **SVM (Kernel RBF)** | 0,44 | 32,44 | 99,67% | 0,9967 |

> **Destaque Operacional:** O classificador **CatBoost** combina acurácia de **99,95%** com latência unitária de apenas **3,90 $\mu$s/fluxo** em CPU (67% mais rápido que o *Random Forest*), viabilizando vazão teórica superior a **250.000 fluxos/segundo por núcleo** para embarque em *firewalls* NGFW e sistemas NIDS.

---

## 🎓 Créditos Acadêmicos

* **Autor:** Álvaro de Souza Ribeiro
* **Orientador:** Prof. Dalbert Matos Mascarenhas
* **Instituição:** Centro Federal de Educação Tecnológica Celso Suckow da Fonseca (CEFET/RJ) — *Campus* Petrópolis
* **Curso:** Bacharelado em Engenharia de Computação (2026)