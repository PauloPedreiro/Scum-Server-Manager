# 🔄 Fluxo de Processamento de Logs via GUI

## 📋 Como Funciona

Quando você executa `main.py --gui`, acontece o seguinte:

1. **GUI é aberta** (`gui_runner.py` → `MainWindow`)
2. **Backend NÃO é iniciado automaticamente**
3. **Você precisa clicar no botão "Start"** na GUI para iniciar o backend
4. Quando o botão "Start" é clicado:
   - Valida licença do equipamento
   - Se válida, inicia processo do backend (`main.py` sem `--gui`)
   - O `main.py` chama `init_components()`
   - `init_components()` inicializa o `LogProcessor`
   - `LogProcessor.start_processing(real_time=True)` é chamado em thread separada
   - Sistema começa a monitorar e processar arquivos `login_*.log`

## ✅ Verificações

### 1. Verificar se Backend está Rodando

```bash
# Testar se API está respondendo
curl http://127.0.0.1:3000/api/health
```

Ou execute:
```bash
python test_backend_logs.py
```

### 2. Verificar se LogProcessor está Ativo

Olhe na GUI:
- Status do backend deve mostrar "Running" (verde)
- Logs devem mostrar: "Inicializando sistema de processamento de logs..."
- Logs devem mostrar: "Sistema de processamento de logs iniciado em thread separada"

### 3. Verificar Processamento de Logs

Quando um novo jogador faz login:
- O arquivo `login_*.log` é detectado pelo monitor
- Arquivo é copiado para `data/temp/`
- Sessões são extraídas e processadas
- Novo jogador é detectado
- Steam Community XML API é consultada
- Notificação é enviada para Discord

## 🔍 Troubleshooting

### Problema: Backend não está processando logs

**Sintomas:**
- Backend está rodando (status "Running")
- Mas não há notificações no Discord
- Logs não mostram processamento de arquivos

**Soluções:**

1. **Verificar se LogProcessor foi inicializado:**
   - Procure nos logs: "Inicializando sistema de processamento de logs..."
   - Se não aparecer, há erro na inicialização

2. **Verificar diretório de logs:**
   - Abra `config.json`
   - Verifique `scum_server.logs_directory`
   - Certifique-se que o caminho está correto

3. **Verificar se arquivos login_*.log existem:**
   ```powershell
   dir "C:\Servers\scum\SCUM\Saved\SaveFiles\Logs\login_*.log"
   ```

4. **Verificar webhook do Discord:**
   - Abra `data/webhooks.json`
   - Verifique se `new_player` tem uma URL válida

5. **Reiniciar backend:**
   - Clique em "Stop" na GUI
   - Aguarde alguns segundos
   - Clique em "Start" novamente

### Problema: Notificações não são enviadas

**Sintomas:**
- Logs mostram processamento de arquivos
- Novos jogadores são detectados
- Mas não há notificações no Discord

**Soluções:**

1. **Verificar webhook:**
   ```bash
   # Testar webhook manualmente
   curl -X POST "URL_DO_WEBHOOK" -H "Content-Type: application/json" -d '{"content":"Teste"}'
   ```

2. **Verificar logs do PlayerProcessor:**
   - Procure por: "NOVO JOGADOR"
   - Procure por: "Notificação de novo jogador enviada"
   - Se não aparecer, há erro no envio

3. **Verificar Steam API:**
   - Logs devem mostrar: "Consultando Steam Community XML API"
   - Se houver erro, verifique conexão com internet

## 📊 Logs Importantes

Procure por estas mensagens nos logs da GUI:

```
✅ "Inicializando sistema de processamento de logs..."
✅ "Sistema de processamento de logs iniciado em thread separada"
✅ "PROCESSANDO Processando arquivo: login_*.log"
✅ "OK Arquivo copiado para temp"
✅ "NOVO JOGADOR"
✅ "Consultando Steam Community XML API"
✅ "Notificação de novo jogador enviada"
```

## 🚀 Teste Rápido

1. Execute `python main.py --gui`
2. Clique em "Start" na GUI
3. Aguarde backend iniciar (status "Running")
4. Faça login com um novo jogador no servidor SCUM
5. Verifique se notificação aparece no Discord
6. Verifique logs na GUI para confirmar processamento

## 📝 Notas Importantes

- **Backend só processa quando está rodando** (botão Start clicado)
- **Logs são processados em tempo real** quando arquivos são modificados
- **Arquivos existentes são processados** quando backend inicia
- **Notificações são enviadas apenas para novos jogadores** (primeira vez no servidor)

