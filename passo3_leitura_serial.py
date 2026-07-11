from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import serial
import serial.tools.list_ports

# =============================================================
# PASSO 3 - LEITURA SERIAL x, y, z
# =============================================================
# x = áudio original
# y = áudio filtrado pelo FIR passa-baixas
# z = parte removida pelo filtro: x - y

PORTA = "COM3"       # Altere para a porta da ESP32-A1S
BAUD = 921_600
TIMEOUT = 3

FS_AUDIO = 48_000
PASSO_SERIAL = 16
FS_EXIBICAO = FS_AUDIO / PASSO_SERIAL  # 3000 pontos por segundo do áudio

PASTA_SCRIPT = Path(__file__).resolve().parent
ARQUIVO_CSV = PASTA_SCRIPT / "dados_fir_300hz.csv"
ARQUIVO_GRAFICO = PASTA_SCRIPT / "graficos_serial_fir_300hz.png"


def listar_portas() -> None:
    portas = list(serial.tools.list_ports.comports())
    if not portas:
        print("Nenhuma porta serial foi encontrada.")
        return

    print("Portas seriais encontradas:")
    for porta in portas:
        print(f"  {porta.device}: {porta.description}")


listar_portas()

entrada = []
filtrado = []
removido = []

print(f"\nAbrindo {PORTA} em {BAUD} bps...")
print("Aguardando os dados da ESP32-A1S.")

try:
    with serial.Serial(PORTA, BAUD, timeout=TIMEOUT) as ser:
        # Ao abrir a porta, algumas placas reiniciam. Limpa dados antigos.
        ser.reset_input_buffer()

        while True:
            bruto = ser.readline()

            if not bruto:
                # Continua esperando enquanto o ESP32 estiver processando.
                continue

            linha = bruto.decode("utf-8", errors="ignore").strip()

            if not linha:
                continue

            if linha.startswith("FIM_ARQUIVO"):
                print(linha)
                break

            partes = linha.split(',')
            if len(partes) != 3:
                # Exibe mensagens como WAV_OK e FIR_OK.
                print(linha)
                continue

            try:
                x, y, z = map(float, partes)
            except ValueError:
                print(linha)
                continue

            entrada.append(x)
            filtrado.append(y)
            removido.append(z)

except serial.SerialException as erro:
    raise SystemExit(
        f"Não foi possível abrir a porta {PORTA}: {erro}\n"
        "Altere a variável PORTA no início do script."
    ) from erro

if not entrada:
    raise SystemExit("Nenhuma linha x,y,z foi recebida.")

entrada_np = np.asarray(entrada)
filtrado_np = np.asarray(filtrado)
removido_np = np.asarray(removido)
tempo = np.arange(len(entrada_np)) / FS_EXIBICAO

# Salva os dados recebidos para usar no relatório/apresentação.
dados = np.column_stack((tempo, entrada_np, filtrado_np, removido_np))
np.savetxt(
    ARQUIVO_CSV,
    dados,
    delimiter=',',
    header="tempo_s,x_original,y_filtrado,z_removido",
    comments='',
    fmt="%.8f",
)

fig, eixos = plt.subplots(4, 1, figsize=(12, 10), sharex=True)

# 1) Áudio original
eixos[0].plot(tempo, entrada_np, linewidth=0.8)
eixos[0].set_title("Áudio original - x[n]")
eixos[0].set_ylabel("Amplitude")
eixos[0].grid(True)

# 2) Áudio filtrado
eixos[1].plot(tempo, filtrado_np, linewidth=0.8)
eixos[1].set_title("Áudio filtrado pelo FIR passa-baixas de 300 Hz - y[n]")
eixos[1].set_ylabel("Amplitude")
eixos[1].grid(True)

# 3) Parte rejeitada pelo filtro
eixos[2].plot(tempo, removido_np, linewidth=0.8)
eixos[2].set_title("Componente removida - z[n] = x[n] - y[n]")
eixos[2].set_ylabel("Amplitude")
eixos[2].grid(True)

# 4) Comparação direta
eixos[3].plot(tempo, entrada_np, linewidth=0.8, label="Original x[n]")
eixos[3].plot(tempo, filtrado_np, linewidth=0.8, label="Filtrado y[n]")
eixos[3].set_title("Comparação: áudio original e áudio filtrado")
eixos[3].set_xlabel("Tempo do áudio (s)")
eixos[3].set_ylabel("Amplitude")
eixos[3].grid(True)
eixos[3].legend()

fig.suptitle("Filtro FIR passa-baixas de 300 Hz na ESP32-A1S")
fig.tight_layout()
fig.savefig(ARQUIVO_GRAFICO, dpi=180)

print(f"\nPontos recebidos: {len(entrada_np)}")
print(f"Taxa representada no gráfico: {FS_EXIBICAO:.0f} pontos/s")
print(f"CSV salvo em: {ARQUIVO_CSV}")
print(f"Gráfico salvo em: {ARQUIVO_GRAFICO}")

plt.show()
