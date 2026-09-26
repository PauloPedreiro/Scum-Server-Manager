# Como Corrigir Ícones dos Executáveis no Windows

Se os executáveis não estão mostrando o ícone correto no explorador de arquivos ou se o ícone na barra de tarefas está muito pequeno, siga estas instruções:

## 🔧 Solução 1: Limpar Cache de Ícones do Windows

O Windows armazena ícones em cache. Se o ícone não aparecer corretamente, limpe o cache:

### Método Automático (PowerShell):

1. Abra o PowerShell como **Administrador**
2. Execute o script:
   ```powershell
   .\tools\refresh_icons.ps1
   ```

### Método Manual:

1. Pressione `Ctrl + Shift + Esc` para abrir o Gerenciador de Tarefas
2. Encontre o processo `Windows Explorer` (explorer.exe)
3. Clique com botão direito → **Finalizar tarefa**
4. No Gerenciador de Tarefas, clique em **Arquivo** → **Executar nova tarefa**
5. Digite `explorer` e pressione Enter
6. Navegue até a pasta `dist` e verifique os ícones

### Método via CMD (como Administrador):

```cmd
taskkill /f /im explorer.exe
del /a /q /f /s "%LOCALAPPDATA%\IconCache.db"
del /a /q /f /s "%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache*.db"
start explorer.exe
```

## 🔧 Solução 2: Verificar se o Ícone foi Aplicado

1. Verifique se o arquivo `Logo_SSM_Multi.ico` existe em `data/imagens/LogoSSM/`
2. Verifique se o spec file está usando o ícone correto
3. Recompile o projeto: `python build.py`

## 🔧 Solução 3: Forçar Atualização do Ícone

1. Feche todos os exploradores de arquivos abertos
2. Reinicie o computador (garante limpeza completa do cache)
3. Após reiniciar, navegue até a pasta `dist`
4. Os ícones devem aparecer corretamente

## 🔧 Solução 4: Verificar o Arquivo ICO

O arquivo ICO precisa ter múltiplos tamanhos embutidos. Para recriar o ícone:

```bash
python tools/create_multi_size_icon.py
```

Isso criará `Logo_SSM_Multi.ico` com os tamanhos:
- 256x256 (alta resolução)
- 128x128 (ícones grandes)
- 64x64 (ícones médios)
- 48x48 (ícones padrão)
- 32x32 (ícones pequenos)
- 16x16 (ícones muito pequenos)

## 📝 Notas Importantes

1. **Cache do Windows**: O Windows pode demorar alguns segundos para atualizar os ícones após limpar o cache
2. **Reiniciar Explorer**: Sempre reinicie o Explorer após limpar o cache
3. **Múltiplos Tamanhos**: Um arquivo ICO com múltiplos tamanhos garante melhor compatibilidade
4. **PyInstaller**: O PyInstaller aplica o ícone durante a compilação. Se não aparecer, pode ser cache do Windows

## ✅ Verificação

Após limpar o cache e recompilar:

1. Navegue até `dist/`
2. Verifique se `ssm_gui.exe` mostra o ícone do SSM
3. Execute `ssm_gui.exe` e verifique se o ícone na barra de tarefas está grande e visível

Se ainda não funcionar, pode ser necessário:
- Usar uma ferramenta externa para criar o ICO (como IcoFX ou GIMP)
- Verificar se o arquivo ICO não está corrompido
- Tentar usar um arquivo PNG convertido para ICO com ferramenta especializada

