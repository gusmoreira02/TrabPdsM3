PROJETO FIR PASSA-BAIXAS DE 300 Hz - ESP32-A1S

Estrutura:
1) passo1_filtro_fir_300hz.py
   - Projeta o FIR com fs = 48000 Hz, fc = 300 Hz, N = 401 e janela de Hamming.
   - Gera automaticamente o arquivo h_fir.h.
   - Mostra a resposta do filtro e um teste com 200 Hz e 1000 Hz.

2) main.cpp
   - Deve ficar na pasta src do projeto PlatformIO.
   - Lê /sinal.wav do cartão SD.
   - Aplica o FIR amostra por amostra.
   - Envia x,y,z pela Serial em 921600 bps.

3) passo3_leitura_serial.py
   - Lê x,y,z da porta serial.
   - Plota áudio original, filtrado, componente removida e comparação.
   - Salva um CSV e uma imagem PNG.

4) h_fir.h
   - Deve ficar na pasta include do projeto PlatformIO.
   - É gerado pelo PASSO 1.

Formato do áudio:
- Nome: sinal.wav
- Local: raiz do cartão SD
- WAV PCM
- 16 bits
- mono ou estéreo
- 48000 Hz

Estrutura sugerida no PlatformIO:
projeto/
  include/
    h_fir.h
  src/
    main.cpp
  scripts_python/
    passo1_filtro_fir_300hz.py
    passo3_leitura_serial.py

Pacotes Python:
pip install numpy matplotlib pyserial

Ordem de execução:
1. Rode passo1_filtro_fir_300hz.py.
2. Copie h_fir.h para include/.
3. Copie main.cpp para src/.
4. Coloque sinal.wav na raiz do SD.
5. Grave o programa na ESP32-A1S.
6. Feche o Serial Monitor.
7. Ajuste PORTA no passo3_leitura_serial.py e execute o script.

