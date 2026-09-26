# Regras de Escopo para o Assistente Gemini/Antigravity

## 🎯 Escopo do Projeto
O desenvolvimento deve ser restrito exclusivamente a este diretório do Backend:
* `C:\Projetos\SSM\SSM 3.0\Backend`

## 🚫 Diretórios e Arquivos a Ignorar
Para economizar tokens, evitar lentidão e focar apenas no código fonte relevante, o assistente **NUNCA** deve ler, analisar ou alterar arquivos nas seguintes pastas:

* `**/dist/**` (arquivos de build e executáveis compilados)
* `**/.venv/**` e `**/venv/**` (ambiente virtual Python)
* `**/.cursor/**`, `**/.vscode/**`, `**/.windsurf/**` (pastas de configuração do editor)
* `**/__pycache__/**` (arquivos de cache do Python)
* `**/node_modules/**` (se houver)

## 📋 Regra de Ouro
1. **Sempre ler o arquivo** antes de fazer qualquer alteração (ferramenta de visualização de arquivos).
2. Não fazer suposições sobre o conteúdo existente.
3. Não realizar buscas ou buscas globais fora do diretório do Backend.
