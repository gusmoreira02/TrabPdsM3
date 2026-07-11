from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# =============================================================
# PASSO 1 - PROJETO DO FILTRO FIR PASSA-BAIXAS
# =============================================================
# O áudio informado possui fs = 48 kHz.
# O filtro deve preservar 200 Hz e atenuar 1000 Hz.

FS = 48_000          # Frequência de amostragem do WAV, em Hz
FC = 300             # Frequência de corte do passa-baixas, em Hz
N = 401              # Número de coeficientes (ímpar)
NFFT = 65_536

PASTA_SCRIPT = Path(__file__).resolve().parent
ARQUIVO_HEADER = PASTA_SCRIPT / "h_fir.h"
ARQUIVO_GRAFICO = PASTA_SCRIPT / "projeto_filtro_fir_300hz.png"

if N % 2 == 0:
    raise ValueError("N precisa ser ímpar.")

if not 0 < FC < FS / 2:
    raise ValueError("FC precisa estar entre 0 e FS/2.")

# 1) Vetor n centralizado
n = np.arange(-(N - 1) // 2, (N - 1) // 2 + 1)

# 2) Resposta ao impulso ideal do passa-baixas
# h_d[n] = 2*fc/fs, para n = 0
# h_d[n] = sen(2*pi*fc*n/fs)/(pi*n), para n != 0
hd = np.empty(N, dtype=float)
hd[n == 0] = 2.0 * FC / FS
hd[n != 0] = np.sin(2.0 * np.pi * FC * n[n != 0] / FS) / (
    np.pi * n[n != 0]
)

# 3) Aplicação da janela de Hamming
janela = np.hamming(N)
h = hd * janela

# 4) Normalização para ganho unitário em 0 Hz
h /= np.sum(h)

# 5) Resposta em frequência
H = np.fft.rfft(h, NFFT)
f = np.fft.rfftfreq(NFFT, d=1.0 / FS)
magnitude = np.abs(H)
magnitude_db = 20.0 * np.log10(magnitude + 1e-12)


def ganho_em(freq_hz: float) -> tuple[float, float]:
    """Retorna magnitude linear e em dB na frequência desejada."""
    indice = int(np.argmin(np.abs(f - freq_hz)))
    return float(magnitude[indice]), float(magnitude_db[indice])


ganho_200, ganho_200_db = ganho_em(200)
ganho_1000, ganho_1000_db = ganho_em(1000)

# 6) Teste sintético com a mesma sequência descrita no trabalho:
#    0 a 3 s: 200 Hz
#    3 a 6 s: 200 Hz + 1000 Hz
#    6 a 9 s: 1000 Hz
DURACAO_TRECHO = 3.0
t = np.arange(0.0, 3.0 * DURACAO_TRECHO, 1.0 / FS)
x = np.zeros_like(t)

m1 = t < DURACAO_TRECHO
m2 = (t >= DURACAO_TRECHO) & (t < 2.0 * DURACAO_TRECHO)
m3 = t >= 2.0 * DURACAO_TRECHO

x[m1] = np.sin(2.0 * np.pi * 200.0 * t[m1])
x[m2] = (
    np.sin(2.0 * np.pi * 200.0 * t[m2])
    + 0.7 * np.sin(2.0 * np.pi * 1000.0 * t[m2])
)
x[m3] = 0.7 * np.sin(2.0 * np.pi * 1000.0 * t[m3])

y = np.convolve(x, h, mode="same")

# Envelope RMS para visualizar claramente os três trechos no tempo.
tamanho_janela_rms = int(0.050 * FS)  # 50 ms
kernel_rms = np.ones(tamanho_janela_rms) / tamanho_janela_rms
rms_x = np.sqrt(np.convolve(x**2, kernel_rms, mode="same"))
rms_y = np.sqrt(np.convolve(y**2, kernel_rms, mode="same"))

# 7) Gráficos do projeto e da validação
fig, eixos = plt.subplots(4, 1, figsize=(11, 11))

# Resposta ao impulso
eixos[0].stem(n, h, basefmt=" ")
eixos[0].set_title("Resposta ao impulso do FIR passa-baixas")
eixos[0].set_xlabel("n")
eixos[0].set_ylabel("h[n]")
eixos[0].grid(True)

# Resposta em frequência em dB
eixos[1].plot(f, magnitude_db)
eixos[1].axvline(FC, linestyle="--", label=f"fc = {FC} Hz")
eixos[1].axvline(200, linestyle=":", label="200 Hz")
eixos[1].axvline(1000, linestyle=":", label="1000 Hz")
eixos[1].set_xlim(0, 2000)
eixos[1].set_ylim(-100, 5)
eixos[1].set_title("Resposta em frequência do filtro")
eixos[1].set_xlabel("Frequência (Hz)")
eixos[1].set_ylabel("Magnitude (dB)")
eixos[1].grid(True)
eixos[1].legend()

# Sinal de teste completo
eixos[2].plot(t, x, label="Entrada")
eixos[2].plot(t, y, label="Saída FIR")
eixos[2].set_title("Teste sintético: entrada e saída")
eixos[2].set_xlabel("Tempo (s)")
eixos[2].set_ylabel("Amplitude")
eixos[2].grid(True)
eixos[2].legend()

# Envelope RMS para evidenciar a rejeição de 1000 Hz
eixos[3].plot(t, rms_x, label="RMS da entrada")
eixos[3].plot(t, rms_y, label="RMS da saída")
eixos[3].set_title("Comparação por envelope RMS")
eixos[3].set_xlabel("Tempo (s)")
eixos[3].set_ylabel("Amplitude RMS")
eixos[3].grid(True)
eixos[3].legend()

fig.tight_layout()
fig.savefig(ARQUIVO_GRAFICO, dpi=180)

# 8) Geração do arquivo .h usado pelo ESP32
with ARQUIVO_HEADER.open("w", encoding="utf-8") as arquivo:
    arquivo.write("#pragma once\n\n")
    arquivo.write("// Arquivo gerado por passo1_filtro_fir_300hz.py\n")
    arquivo.write("// FIR passa-baixas: fc = 300 Hz, fs = 48000 Hz, janela de Hamming\n")
    arquivo.write(f"#define N {N}\n")
    arquivo.write(f"#define FS_FILTRO {FS}.0f\n")
    arquivo.write(f"#define FC_FILTRO {FC}.0f\n\n")
    arquivo.write("const float h[N] = {\n")
    for i, coeficiente in enumerate(h):
        separador = "," if i < len(h) - 1 else ""
        arquivo.write(f"    {coeficiente:.10e}f{separador}\n")
    arquivo.write("};\n")

print("Filtro FIR passa-baixas projetado com sucesso.")
print(f"fs = {FS} Hz | fc = {FC} Hz | N = {N} | janela = Hamming")
print(f"Ganho em 200 Hz:  {ganho_200:.6f} ({ganho_200_db:.2f} dB)")
print(f"Ganho em 1000 Hz: {ganho_1000:.6f} ({ganho_1000_db:.2f} dB)")
print(f"Atraso do FIR: {(N - 1) / 2:.0f} amostras = {1000 * (N - 1) / (2 * FS):.3f} ms")
print(f"Header gerado em: {ARQUIVO_HEADER}")
print(f"Gráfico salvo em: {ARQUIVO_GRAFICO}")

plt.show()
