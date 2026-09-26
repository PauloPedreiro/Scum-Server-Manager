# Guia de Compilação do GUI Desktop

Este documento explica como compilar a interface gráfica (GUI) do SSM Backend em um executável `.exe`.

## 📋 Pré-requisitos

1. **Python 3.8+** instalado
2. **PyInstaller** instalado (será instalado automaticamente se não estiver)
3. **Todas as dependências** do projeto instaladas:
   ```bash
   pip install -r requirements.txt
   ```

## 🔧 Dependências Específicas do GUI

O GUI utiliza as seguintes bibliotecas principais:
- `customtkinter` - Framework de interface gráfica moderna
- `Pillow` (PIL) - Processamento de imagens
- `pyperclip` - Acesso à área de transferência
- `psutil` - Informações do sistema (opcional)
- `requests` - Requisições HTTP (opcional)

Todas essas dependências já estão listadas no `requirements.txt`.

## 🚀 Como Compilar

### Método 1: Usando o Script de Build (Recomendado)

Execute o script de build que compila todos os executáveis, incluindo o GUI:

```bash
python build.py
```

Este script irá:
1. Verificar se o PyInstaller está instalado
2. Limpar builds anteriores
3. Compilar todos os executáveis usando o arquivo `ssm_backend.spec`:
   - `ssm_backend.exe` - Backend API
   - `ssm_gui.exe` - **Interface Gráfica Desktop**
   - `config_editor.exe` - Editor de configuração
   - `launcher.exe` - Launcher com verificação

### Método 2: Compilação Manual com PyInstaller

Se preferir compilar apenas o GUI manualmente:

```bash
pyinstaller --name=ssm_gui --windowed --icon=data/imagens/LogoSSM/Logo_SSM_256x256.ico gui/gui_runner.py
```

**Nota:** Este método não incluirá automaticamente todos os arquivos de dados necessários. É recomendado usar o método 1.

## 📁 Estrutura do Executável

O executável `ssm_gui.exe` será criado na pasta `dist/` junto com:

- **ssm_gui.exe** - Executável principal da GUI
- **data/** - Arquivos de configuração, imagens e templates
- **base_coordinates.csv** e **base_coordinates.json** - Coordenadas base
- **Pasta _internal/** - Bibliotecas e dependências empacotadas

## ⚙️ Configuração do Spec File

O arquivo `ssm_backend.spec` contém a configuração completa para compilar o GUI. As principais configurações incluem:

### Dados Incluídos
- Arquivos de configuração (`config.example.json`, `webhooks.example.json`)
- Diretório completo de imagens (`data/imagens/`)
- Templates de notificações
- Arquivos de coordenadas base

### Imports Ocultos
O spec file inclui todos os módulos necessários:
- Módulos do GUI (`customtkinter`, `PIL`, `pyperclip`)
- Módulos do core (server_manager, licensing, etc.)
- Utilitários e helpers

### Configurações do Executável
- **Nome:** `ssm_gui.exe`
- **Console:** Desabilitado (aplicação GUI windowed)
- **Ícone:** `Logo_SSM_256x256.ico`
- **UPX:** Habilitado (compressão)

## 🎯 Executando o GUI Compilado

Após a compilação, você pode executar o GUI de duas formas:

1. **Diretamente:**
   ```bash
   dist\ssm_gui.exe
   ```

2. **Via Launcher:**
   ```bash
   dist\launcher.exe
   ```
   O launcher pode abrir o GUI automaticamente.

## 🔍 Solução de Problemas

### Erro: "PyInstaller não encontrado"
```bash
pip install pyinstaller
```

### Erro: "Módulo não encontrado"
Certifique-se de que todas as dependências estão instaladas:
```bash
pip install -r requirements.txt
```

### Erro: "Ícone não encontrado"
Verifique se o arquivo `data/imagens/LogoSSM/Logo_SSM_256x256.ico` existe. Se não existir, o build continuará sem ícone.

### GUI não inicia após compilação
1. Verifique se todos os arquivos de `data/` foram copiados para `dist/`
2. Execute o executável via terminal para ver mensagens de erro:
   ```bash
   dist\ssm_gui.exe
   ```
3. Verifique se há dependências faltando no spec file

### Executável muito grande
O executável pode ser grande devido às dependências incluídas. Para reduzir:
- Remova módulos não utilizados do `hiddenimports` no spec file
- Use UPX (já habilitado por padrão)
- Considere usar `--onefile` vs `--onedir` (atualmente usando `--onedir`)

## 📝 Notas Importantes

1. **Primeira Execução:** Na primeira execução, o PyInstaller pode demorar alguns minutos para compilar.

2. **Antivírus:** Alguns antivírus podem marcar executáveis do PyInstaller como suspeitos. Isso é um falso positivo comum.

3. **Distribuição:** Para distribuir o GUI, copie toda a pasta `dist/` ou pelo menos:
   - `ssm_gui.exe`
   - Pasta `_internal/` (se existir)
   - Pasta `data/`
   - Arquivos `base_coordinates.*`

4. **Atualizações:** Após modificar o código do GUI, execute `python build.py` novamente para recompilar.

## 🔄 Atualizando o Spec File

Se você adicionar novas dependências ou módulos ao GUI, atualize o arquivo `ssm_backend.spec`:

1. Adicione novos módulos em `hiddenimports` da seção `gui`
2. Adicione novos arquivos de dados em `gui_datas`
3. Execute `python build.py` novamente

## 📚 Referências

- [Documentação do PyInstaller](https://pyinstaller.org/)
- [Documentação do CustomTkinter](https://customtkinter.tomschimansky.com/)
- [Documentação do PIL/Pillow](https://pillow.readthedocs.io/)

