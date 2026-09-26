# Correção do Launcher - Problema de Fechamento Rápido

## 🔧 Problema Identificado

O `launcher.exe` estava fechando rapidamente porque:

1. **Caminhos incorretos**: Quando executado como .exe, os caminhos relativos não funcionavam
2. **Falta de tratamento de erros**: Erros não eram exibidos antes de fechar
3. **Sem pausa**: O console fechava imediatamente após erro

## ✅ Correções Implementadas

### 1. Detecção de Modo de Execução

O launcher agora detecta se está rodando como:
- **Executável (.exe)**: Usa `sys._MEIPASS` e `sys.executable`
- **Script Python**: Usa caminhos relativos normais

### 2. Caminhos Corrigidos

```python
if getattr(sys, 'frozen', False):
    # Modo executável
    ROOT_DIR = Path(sys._MEIPASS)  # Diretório temporário
    EXE_DIR = Path(sys.executable).parent  # Onde o .exe está
else:
    # Modo script
    ROOT_DIR = Path(__file__).parent.parent
    EXE_DIR = ROOT_DIR
```

### 3. Arquivos de Configuração

Os arquivos `config.json` e `webhooks.json` são criados/verificados em:
- **Modo executável**: `{diretório_do_exe}/data/`
- **Modo script**: `{raiz_do_projeto}/data/`

### 4. Tratamento de Erros Global

```python
try:
    main()
except Exception as e:
    print("ERRO FATAL")
    traceback.print_exc()
    wait_before_exit()
    sys.exit(1)
```

### 5. Pausa Antes de Fechar

Função `wait_before_exit()` que:
- Aguarda Enter do usuário (se console disponível)
- Ou aguarda 5 segundos (se sem console)

### 6. Chamadas Corretas

- **Backend**: Chama `ssm_backend.exe` quando executável, `main.py` quando script
- **Editor**: Chama `config_editor.exe` quando executável, `config_editor.py` quando script

## 🚀 Como Testar

### Teste como Script (Desenvolvimento)

```bash
python tools/launcher.py
```

### Teste como Executável

1. Rebuild o executável:
   ```bash
   python build.py
   ```

2. Execute o launcher:
   ```bash
   dist/ssm_backend/launcher.exe
   ```

3. Verifique:
   - Console permanece aberto
   - Mensagens são exibidas
   - Erros são mostrados claramente
   - Pausa antes de fechar

## 📝 Notas Importantes

- O launcher agora cria o diretório `data/` automaticamente se não existir
- Arquivos de exemplo são copiados durante o build
- Todos os caminhos são relativos ao diretório do executável quando em modo .exe

## 🔍 Debug

Se ainda houver problemas:

1. Execute via linha de comando para ver erros:
   ```cmd
   cd dist\ssm_backend
   launcher.exe
   ```

2. Verifique se os arquivos existem:
   - `ssm_backend.exe`
   - `config_editor.exe`
   - `data/config.example.json`
   - `data/webhooks.example.json`

3. Verifique permissões de escrita no diretório


