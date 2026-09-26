# 📦 Sistema de Gerenciamento de Versão

Sistema automatizado para gerenciar a versão do SSM Backend.

## 🎯 Como Funciona

A versão está centralizada em `version.py` e é usada automaticamente em:
- ✅ Título da GUI (`SSM Backend v3.0.1`)
- ✅ Validação de licença (enviada ao servidor de gestão)
- ✅ Sincronização com Gestão
- ✅ Todos os lugares que importam `VERSION`

## 🚀 Métodos de Atualização

### 1. **Script Manual** (Recomendado)

```bash
# Mostrar versão atual
python tools/update_version.py show

# Definir versão manualmente
python tools/update_version.py set 3.0.2

# Incrementar patch (3.0.1 -> 3.0.2)
python tools/update_version.py patch

# Incrementar minor (3.0.1 -> 3.1.0)
python tools/update_version.py minor

# Incrementar major (3.0.1 -> 4.0.0)
python tools/update_version.py major
```

### 2. **Integração com Git Tags** (Automático)

Atualizar versão baseado na última tag Git:

```bash
# Criar tag Git
git tag v3.0.2

# Atualizar versão automaticamente da tag
python tools/pre_commit_hook.py --auto
```

### 3. **Git Hook Automático** (Opcional)

Para atualizar versão automaticamente antes de cada commit:

```bash
# Copiar hook para .git/hooks/
cp tools/pre_commit_hook.py .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## 📋 Fluxo Recomendado

### Para Nova Versão:

1. **Decidir tipo de atualização:**
   - **Patch** (3.0.100 → 3.0.101): Correções de bugs (incremento de 1)
   - **Patch com valor** (3.0.100 → 3.0.110): Incremento customizado
   - **Build** (3.0.100 → 3.0.XXXXX): Número baseado em timestamp (único)
   - **Minor** (3.0.100 → 3.1.0): Novas funcionalidades
   - **Major** (3.0.100 → 4.0.0): Mudanças incompatíveis

2. **Atualizar versão:**
   ```bash
   # Incremento simples
   python tools/update_version.py patch
   
   # Incremento customizado (útil para muitas versões)
   python tools/update_version.py patch 10  # Incrementa 10
   
   # Usar número de build único (baseado em timestamp)
   python tools/update_version.py build
   ```

3. **Criar tag Git (opcional):**
   ```bash
   git add version.py
   git commit -m "chore: atualizar versão para 3.0.110"
   git tag v3.0.110
   git push origin main --tags
   ```

### 💡 Dica: Números Grandes

Para suportar muitas versões, use números grandes no patch:
- `3.0.100` → `3.0.101` (incremento de 1)
- `3.0.100` → `3.0.110` (incremento de 10)
- `3.0.100` → `3.0.200` (incremento de 100)

Isso permite ter centenas ou milhares de versões sem problemas!

## 🔄 Integração com CI/CD

### GitHub Actions (Exemplo)

```yaml
name: Update Version
on:
  push:
    tags:
      - 'v*'

jobs:
  update-version:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Update version from tag
        run: |
          VERSION=${GITHUB_REF#refs/tags/v}
          python tools/update_version.py set $VERSION
      - name: Commit version
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add version.py
          git commit -m "chore: atualizar versão para $VERSION"
          git push
```

## 📝 Convenções de Versionamento

Seguindo [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Mudanças incompatíveis na API
- **MINOR** (0.X.0): Novas funcionalidades compatíveis
- **PATCH** (0.0.X): Correções de bugs compatíveis

### Exemplos:

- `3.0.1` → `3.0.2`: Correção de bug
- `3.0.1` → `3.1.0`: Nova funcionalidade
- `3.0.1` → `4.0.0`: Mudança incompatível

## ⚠️ Importante

- ✅ Sempre atualize a versão antes de fazer release
- ✅ Use tags Git para marcar releases
- ✅ A versão é usada na validação de licença (enviada ao Gestão)
- ✅ A versão aparece no título da GUI automaticamente

