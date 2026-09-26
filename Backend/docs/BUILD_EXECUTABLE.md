# Guia de Build - Executável SSM Backend

Este guia explica como criar um executável do SSM Backend para distribuição, protegendo o código fonte.

## 📋 Pré-requisitos

1. **Python 3.8+** instalado
2. **Todas as dependências** instaladas:
   ```bash
   pip install -r requirements.txt
   ```
3. **PyInstaller** (já incluído no requirements.txt)

## 🛠️ Processo de Build

### Opção 1: Usando o Script Automático (Recomendado)

```bash
python build.py
```

O script irá:
- Verificar se PyInstaller está instalado
- Limpar builds anteriores
- Criar os executáveis usando o arquivo `ssm_backend.spec`

### Opção 2: Build Manual

```bash
# Limpar builds anteriores
rmdir /s /q build dist

# Criar executável principal
pyinstaller ssm_backend.spec --clean --noconfirm
```

## 📦 Estrutura dos Executáveis

Após o build, você terá na pasta `dist/ssm_backend/`:

```
dist/ssm_backend/
├── ssm_backend.exe      # Executável principal do backend
├── config_editor.exe    # Editor de configuração (interface web)
├── launcher.exe         # Launcher com verificação de config
├── _internal/           # Bibliotecas e dependências
├── data/                # Arquivos de dados (imagens, exemplos)
└── nssm-2.24/          # Utilitários NSSM
```

## 🚀 Como Usar

### Primeira Execução

1. **Execute o launcher:**
   ```bash
   launcher.exe
   ```

2. **Se os arquivos de configuração não existirem:**
   - O launcher abrirá automaticamente o editor de configuração
   - Acesse `http://127.0.0.1:8888` no navegador
   - Configure `config.json` e `webhooks.json`
   - Salve as configurações

3. **Após configurar:**
   - Execute `launcher.exe` novamente
   - O backend será iniciado automaticamente

### Execução Direta

Se já tiver os arquivos configurados:

```bash
ssm_backend.exe
```

### Editor de Configuração Standalone

Para editar configurações depois:

```bash
config_editor.exe
```

Acesse `http://127.0.0.1:8888` no navegador.

## 📝 Arquivos de Configuração

Os arquivos de configuração devem estar em:
- `data/config.json` - Configurações principais
- `data/webhooks.json` - Webhooks do Discord

**Importante:** Os arquivos `config.example.json` e `webhooks.example.json` são incluídos no executável como referência.

## 🔒 Proteção do Código Fonte

O PyInstaller compila o código Python em bytecode e empacota tudo em um executável. O código fonte original **não está acessível** no executável final.

### Níveis de Proteção:

1. **Bytecode Compilado**: Código convertido para `.pyc`
2. **Empacotamento**: Tudo dentro do executável
3. **Obfuscação (Opcional)**: Pode usar ferramentas como `pyarmor` para maior proteção

## 📤 Distribuição

Para distribuir o executável:

1. **Compacte a pasta completa:**
   ```
   dist/ssm_backend/
   ```

2. **Inclua um README** com instruções básicas:
   - Como executar o launcher
   - Como configurar pela primeira vez
   - Requisitos do sistema

3. **Tamanho esperado:** ~50-100 MB (dependendo das dependências)

## ⚙️ Personalização do Build

### Modificar o arquivo `.spec`

Edite `ssm_backend.spec` para:
- Adicionar/remover arquivos em `datas`
- Incluir ícones personalizados
- Ajustar opções de compressão
- Modificar nome do executável

### Exemplo: Adicionar Ícone

```python
exe = EXE(
    ...
    icon='assets/icon.ico',  # Adicione esta linha
    ...
)
```

## 🐛 Troubleshooting

### Erro: "Module not found"

Adicione o módulo faltante em `hiddenimports` no arquivo `.spec`:

```python
hiddenimports=[
    ...
    'nome_do_modulo_faltante',
]
```

### Executável muito grande

1. Use `upx=True` no spec (já está ativado)
2. Remova dependências não utilizadas
3. Use `--exclude-module` para excluir módulos desnecessários

### Erro ao executar

1. Verifique se todos os arquivos de dados estão em `datas`
2. Teste em uma máquina limpa (sem Python instalado)
3. Verifique os logs de erro no console

## 📚 Referências

- [PyInstaller Documentation](https://pyinstaller.org/)
- [PyInstaller Spec File](https://pyinstaller.org/en/stable/spec-files.html)

## 🔄 Atualizações

Para atualizar o executável após mudanças no código:

1. Faça as alterações no código
2. Execute `python build.py` novamente
3. Teste o novo executável
4. Distribua a nova versão

---

**Nota:** O código fonte original permanece no diretório do projeto. O executável é uma cópia compilada e empacotada.


