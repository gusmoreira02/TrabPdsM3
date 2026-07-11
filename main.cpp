#include <Arduino.h>
#include <FS.h>
#include <SPI.h>
#include <SD.h>
#include <string.h>
#include "h_fir.h"

// =============================================================
// PASSO 2 - ESP32 / ESP32-A1S
// Lê um WAV do cartão SD, aplica o FIR passa-baixas de 300 Hz
// e envia três colunas pela Serial:
//
// x = amostra original
// y = amostra filtrada
// z = parte removida pelo filtro, z = x - y
// =============================================================

// Pinos do cartão SD usados no projeto anterior com ESP32-A1S.
// Ajuste somente se a sua placa estiver ligada de outra forma.
#define SD_CS   13
#define SD_SCK  14
#define SD_MISO 2
#define SD_MOSI 15

// O arquivo deve ficar na raiz do cartão.
// Formato esperado: WAV PCM, 16 bits, mono ou estéreo, 48 kHz.
const char *AUDIO_PATH = "/sinal.wav";

// 48.000 / 16 = 3.000 linhas por segundo na Serial.
// Isso ainda permite representar a componente de 1000 Hz no gráfico.
const uint16_t ENVIAR_CADA_N_AMOSTRAS = 16;

// Baud alto porque são enviados três números por linha.
const uint32_t SERIAL_BAUD = 921600;

// Buffer circular do FIR.
float xbuf[N] = {0.0f};
int indiceFIR = 0;

File audioFile;
uint32_t bytesLidosDados = 0;
uint32_t numeroAmostra = 0;

struct WavInfo {
  uint16_t audioFormat = 0;
  uint16_t numChannels = 0;
  uint32_t sampleRate = 0;
  uint16_t bitsPerSample = 0;
  uint32_t dataStart = 0;
  uint32_t dataSize = 0;
};

WavInfo wav;

uint16_t lerLE16(File &arquivo) {
  uint8_t bytes[2];
  if (arquivo.read(bytes, 2) != 2) return 0;
  return (uint16_t)bytes[0] | ((uint16_t)bytes[1] << 8);
}

uint32_t lerLE32(File &arquivo) {
  uint8_t bytes[4];
  if (arquivo.read(bytes, 4) != 4) return 0;
  return (uint32_t)bytes[0]
       | ((uint32_t)bytes[1] << 8)
       | ((uint32_t)bytes[2] << 16)
       | ((uint32_t)bytes[3] << 24);
}

bool lerID(File &arquivo, char id[5]) {
  if (arquivo.read((uint8_t *)id, 4) != 4) return false;
  id[4] = '\0';
  return true;
}

void pularBytes(File &arquivo, uint32_t quantidade) {
  arquivo.seek(arquivo.position() + quantidade);
}

bool abrirWav(const char *caminho) {
  audioFile = SD.open(caminho, FILE_READ);
  if (!audioFile) {
    Serial.println("ERRO: nao foi possivel abrir /sinal.wav.");
    return false;
  }

  char id[5];

  if (!lerID(audioFile, id) || strcmp(id, "RIFF") != 0) {
    Serial.println("ERRO: o arquivo nao possui cabecalho RIFF.");
    return false;
  }

  lerLE32(audioFile);  // Tamanho total do RIFF.

  if (!lerID(audioFile, id) || strcmp(id, "WAVE") != 0) {
    Serial.println("ERRO: o arquivo nao e WAV.");
    return false;
  }

  bool achouFmt = false;
  bool achouData = false;

  while (audioFile.available()) {
    if (!lerID(audioFile, id)) break;

    uint32_t tamanhoChunk = lerLE32(audioFile);

    if (strcmp(id, "fmt ") == 0) {
      wav.audioFormat = lerLE16(audioFile);
      wav.numChannels = lerLE16(audioFile);
      wav.sampleRate = lerLE32(audioFile);
      lerLE32(audioFile);  // byteRate
      lerLE16(audioFile);  // blockAlign
      wav.bitsPerSample = lerLE16(audioFile);

      if (tamanhoChunk > 16) {
        pularBytes(audioFile, tamanhoChunk - 16);
      }
      achouFmt = true;
    } else if (strcmp(id, "data") == 0) {
      wav.dataStart = audioFile.position();
      wav.dataSize = tamanhoChunk;
      achouData = true;
      break;
    } else {
      pularBytes(audioFile, tamanhoChunk);
    }

    // Chunks WAV podem ter um byte de preenchimento.
    if (tamanhoChunk % 2 == 1) {
      pularBytes(audioFile, 1);
    }
  }

  if (!achouFmt || !achouData) {
    Serial.println("ERRO: cabecalho WAV incompleto.");
    return false;
  }

  if (wav.audioFormat != 1 || wav.bitsPerSample != 16) {
    Serial.println("ERRO: use WAV PCM de 16 bits.");
    return false;
  }

  if (wav.numChannels != 1 && wav.numChannels != 2) {
    Serial.println("ERRO: use WAV mono ou estereo.");
    return false;
  }

  if (fabsf((float)wav.sampleRate - FS_FILTRO) > 1.0f) {
    Serial.print("ERRO: fs do WAV = ");
    Serial.print(wav.sampleRate);
    Serial.print(" Hz, mas o filtro foi projetado para ");
    Serial.print(FS_FILTRO, 0);
    Serial.println(" Hz.");
    return false;
  }

  audioFile.seek(wav.dataStart);
  bytesLidosDados = 0;

  Serial.print("WAV_OK,fs=");
  Serial.print(wav.sampleRate);
  Serial.print(",canais=");
  Serial.print(wav.numChannels);
  Serial.print(",bits=");
  Serial.println(wav.bitsPerSample);

  Serial.print("FIR_OK,fc=");
  Serial.print(FC_FILTRO, 0);
  Serial.print(",N=");
  Serial.println(N);

  Serial.println("DADOS,x_original,y_filtrado,z_removido");
  return true;
}

bool lerAmostraWav(float &x) {
  const uint32_t bytesPorQuadro = wav.numChannels * sizeof(int16_t);

  if (bytesLidosDados + bytesPorQuadro > wav.dataSize) {
    return false;
  }

  int16_t amostra1 = (int16_t)lerLE16(audioFile);
  bytesLidosDados += sizeof(int16_t);

  if (wav.numChannels == 2) {
    int16_t amostra2 = (int16_t)lerLE16(audioFile);
    bytesLidosDados += sizeof(int16_t);
    int32_t media = ((int32_t)amostra1 + (int32_t)amostra2) / 2;
    x = (float)media / 32768.0f;
  } else {
    x = (float)amostra1 / 32768.0f;
  }

  return true;
}

float aplicarFIR(float x) {
  xbuf[indiceFIR] = x;

  float y = 0.0f;
  int j = indiceFIR;

  for (int i = 0; i < N; i++) {
    y += h[i] * xbuf[j];
    j--;
    if (j < 0) j = N - 1;
  }

  indiceFIR++;
  if (indiceFIR >= N) indiceFIR = 0;

  return y;
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(1500);

  Serial.println("Iniciando SD -> FIR 300 Hz -> Serial...");

  SPI.begin(SD_SCK, SD_MISO, SD_MOSI, SD_CS);
  if (!SD.begin(SD_CS, SPI)) {
    Serial.println("ERRO: falha ao iniciar o cartao SD.");
    while (true) delay(1000);
  }

  if (!abrirWav(AUDIO_PATH)) {
    while (true) delay(1000);
  }
}

void loop() {
  float x = 0.0f;

  if (!lerAmostraWav(x)) {
    Serial.print("FIM_ARQUIVO,amostras=");
    Serial.println(numeroAmostra);
    audioFile.close();
    while (true) delay(1000);
  }

  const float y = aplicarFIR(x);
  const float z = x - y;

  if (numeroAmostra % ENVIAR_CADA_N_AMOSTRAS == 0) {
    Serial.print(x, 5);
    Serial.print(',');
    Serial.print(y, 5);
    Serial.print(',');
    Serial.println(z, 5);
  }

  numeroAmostra++;
}
