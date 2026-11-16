import pandas as pd

# Carrega o CSV (low_memory=False ajuda caso o pandas confunda os tipos devido ao cabeçalho repetido)
df = pd.read_csv("dataset.csv", low_memory=False)

linhas_antes = len(df)

# 1. Remove as linhas onde o cabeçalho foi escrito repetido no meio do arquivo
df = df[df['session_id'] != 'session_id']

# 2. Remove possíveis capturas duplicadas pela condição de corrida
df = df.drop_duplicates(subset=['session_id'], keep='last')

linhas_depois = len(df)

# Salva o arquivo corrigido
df.to_csv("dataset_limpo.csv", index=False)

print(f"Limpeza Concluída!")
print(f"Linhas fantasmas removidas: {linhas_antes - linhas_depois}")
print(f"Total final de amostras: {linhas_depois} (Deverá bater com os seus .pcaps)")