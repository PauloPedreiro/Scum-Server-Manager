# 🖥️ GUI Desktop - SSM Backend

## 📋 Visão Geral

Interface gráfica desktop integrada ao SSM Backend para controle do servidor e gerenciamento de licenciamento.

## 🚀 Como Executar

### Modo GUI (Desktop)

```bash
python main.py --gui
```

### Modo API (Apenas Backend)

```bash
python main.py
```

## 📦 Dependências

Instale as dependências necessárias:

```bash
pip install customtkinter pyperclip
```

Ou instale todas as dependências:

```bash
pip install -r requirements.txt
```

## 🎨 Funcionalidades

### 1. Controles do Servidor

- **Iniciar**: Inicia o servidor SCUM
- **Parar**: Para o servidor SCUM
- **Reiniciar**: Para e inicia o servidor novamente
- **Status**: Indicador visual (verde/vermelho) mostrando se o servidor está rodando

### 2. Hardware Fingerprint

- **Exibição do Hash**: Mostra o hash completo do hardware
- **Copiar Hash**: Botão para copiar o hash para área de transferência
- **Uso**: O hash pode ser usado para cadastrar o equipamento no servidor de licenciamento

## 🔧 Arquitetura

A GUI é integrada ao backend, não é uma aplicação separada:

```
┌─────────────────────────────────┐
│      GUI (CustomTkinter)        │
│  ┌───────────────────────────┐  │
│  │  Acesso Direto aos        │  │
│  │  Componentes do Backend   │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│    Backend Flask (Thread)      │
│  - ServerManager               │
│  - HardwareFingerprint         │
│  - API REST (Port 3000)        │
└─────────────────────────────────┘
```

### Componentes

- **`gui/main_window.py`**: Janela principal com interface
- **`gui/gui_runner.py`**: Integração GUI + Backend
- **`main.py`**: Modificado para suportar modo `--gui`

## 📝 Estrutura de Arquivos

```
gui/
├── __init__.py
├── main_window.py      # Janela principal
└── gui_runner.py       # Runner da GUI

main.py                 # Suporta --gui
```

## 🎯 Próximos Passos

### Compilação em .exe

Após testar e validar a GUI, use PyInstaller para criar o executável:

```bash
pyinstaller --onefile --windowed --name="SSM_Backend" main.py
```

Ou crie um arquivo `.spec` personalizado para incluir todos os recursos necessários.

## 🐛 Troubleshooting

### Erro: "customtkinter não encontrado"

```bash
pip install customtkinter
```

### Erro: "pyperclip não encontrado"

```bash
pip install pyperclip
```

### GUI não inicia

- Verifique se todas as dependências estão instaladas
- Verifique se o backend está configurado corretamente
- Veja os logs no console para mais detalhes

### Botões não funcionam

- Verifique se o ServerManager foi inicializado corretamente
- Verifique se o servidor SCUM está configurado no `config.json`

## 📚 Referências

- [CustomTkinter Documentation](https://customtkinter.tomschimansky.com/)
- [PyInstaller Documentation](https://pyinstaller.org/)

