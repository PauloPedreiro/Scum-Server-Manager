# 📦 Guia de Distribuição - SSM 3.0 Frontend

Este guia explica o que está incluído na pasta `dist/` e como distribuir a aplicação.

## 📋 Conteúdo da Pasta `dist/`

Após executar `npm run build`, a pasta `dist/` conterá:

### Arquivos Essenciais

- ✅ **`index.html`** - Arquivo HTML principal da aplicação
- ✅ **`config.json`** - Configuração do backend (IP, porta, protocolo)
- ✅ **`README.md`** - Instruções de uso (copiado automaticamente)

### Pasta `assets/`

Contém todos os arquivos compilados e otimizados:

- **JavaScript** (`*.js`) - Código da aplicação compilado e minificado
  - `index-*.js` - Bundle principal
  - `Home-*.js`, `Login-*.js`, `Map-*.js`, etc. - Chunks por página
- **CSS** (`*.css`) - Estilos compilados e minificados
  - `index-*.css` - Estilos globais
- **Imagens** - Todos os assets otimizados:
  - Backgrounds (wallpapers)
  - Logos (SSMlogo.png, logoSSM.gif)
  - Mapas (Map.png)
  - Veículos (todos os PNGs de veículos)
  - Baús (todos os PNGs de baús)

## ✅ Checklist de Distribuição

Antes de distribuir a pasta `dist/`, verifique:

- [ ] `index.html` existe
- [ ] `config.json` existe e está configurado corretamente
- [ ] Pasta `assets/` contém todos os arquivos
- [ ] `README.md` está presente (opcional, mas recomendado)

## 🚀 Como Distribuir

### Opção 1: ZIP/TAR

1. Compacte a pasta `dist/` inteira:
   ```bash
   # Windows
   Compress-Archive -Path dist -DestinationPath ssm-frontend-v1.4.1.zip
   
   # Linux/Mac
   tar -czf ssm-frontend-v1.4.1.tar.gz dist/
   ```

2. Distribua o arquivo compactado

3. O usuário deve:
   - Extrair o arquivo
   - Editar `config.json` com o IP do backend
   - Servir os arquivos (veja `README.md` na dist)

### Opção 2: Git

1. Adicione a pasta `dist/` ao repositório (ou crie uma branch `gh-pages`)
2. Faça push
3. Usuários podem clonar ou fazer download

### Opção 3: Servidor Web

1. Faça upload da pasta `dist/` para o servidor
2. Configure Nginx/Apache para servir a pasta
3. Configure HTTPS (recomendado)

## 📝 Notas Importantes

### Arquivos NÃO Incluídos

Estes arquivos **não** precisam estar na `dist/`:

- ❌ `node_modules/` - Não necessário (aplicação já compilada)
- ❌ `src/` - Código-fonte não necessário em produção
- ❌ `package.json` - Não necessário (aplicação standalone)
- ❌ Arquivos de configuração de desenvolvimento (vite.config.ts, tsconfig.json, etc.)

### Arquivos Incluídos Automaticamente

Estes arquivos são incluídos automaticamente no bundle:

- ✅ Traduções (i18n) - Incluídas no JavaScript
- ✅ `mapping.json` de veículos - Incluído no JavaScript
- ✅ Todas as dependências - Incluídas no bundle

### Configuração em Produção

O arquivo `config.json` na `dist/` pode ser editado diretamente pelo usuário:

```json
{
  "backend": {
    "host": "192.168.100.3",  // IP do backend
    "port": 3000,              // Porta do backend
    "protocol": "http",        // ou "https"
    "basePath": "/api",
    "timeout": 60000
  }
}
```

**Importante:** Após editar `config.json`, o usuário precisa recarregar a página no navegador.

## 🔍 Verificação da Distribuição

Execute o script de verificação:

```bash
.\verificar-build.bat
```

Ou verifique manualmente:

```bash
# Windows
dir dist
dir dist\assets

# Linux/Mac
ls -la dist/
ls -la dist/assets/
```

## 📦 Tamanho Esperado

A pasta `dist/` completa deve ter aproximadamente:

- **Tamanho total**: ~15-20 MB (sem compressão)
- **Tamanho comprimido (ZIP)**: ~5-8 MB
- **Número de arquivos**: ~60-70 arquivos

## 🎯 Próximos Passos

Após distribuir:

1. Usuário extrai a pasta `dist/`
2. Usuário edita `config.json`
3. Usuário serve os arquivos (veja `README.md`)
4. Usuário acessa `http://localhost:5173` (ou IP do servidor)

---

**Última atualização**: 2025-01-27

