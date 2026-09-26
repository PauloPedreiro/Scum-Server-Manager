# 🚀 Guia de Inicialização em Produção - SSM 3.0 Frontend

Este guia detalha como fazer o build e iniciar a aplicação em produção.

## 📋 Pré-requisitos

- Node.js >= 18.0.0 instalado
- Backend configurado e acessível
- Configuração do backend em `src/config.json` atualizada para produção

## 🏗️ Passo 1: Build para Produção

Execute o comando de build para gerar os arquivos otimizados:

```bash
npm run build
```

Este comando irá:
- ✅ Compilar TypeScript para JavaScript
- ✅ Minificar JavaScript e CSS
- ✅ Otimizar imagens e assets
- ✅ Gerar a pasta `dist/` com arquivos prontos para produção

**Tempo estimado**: 30-60 segundos

### Verificar Build

Após o build, verifique se a pasta `dist/` foi criada:

```bash
# Windows (PowerShell)
dir dist

# Linux/Mac
ls -la dist
```

Você deve ver arquivos como:
- `index.html`
- `assets/` (com JS, CSS e imagens otimizadas)

---

## 🌐 Passo 2: Servir a Aplicação em Produção

Existem várias opções para servir a aplicação. Escolha a que melhor se adequa ao seu ambiente:

### Opção 1: Usando `serve` (Recomendado para testes rápidos)

#### Instalação Global

```bash
npm install -g serve
```

#### Iniciar o Servidor

```bash
serve -s dist -l 5173
```

**Parâmetros:**
- `-s dist`: Serve a pasta `dist/` (modo SPA - Single Page Application)
- `-l 5173`: Porta 5173 (ou use outra porta)

**Acessar:**
- Local: `http://localhost:5173`
- Rede: `http://[SEU_IP]:5173`

#### Parar o Servidor

Pressione `Ctrl + C` no terminal.

---

### Opção 2: Usando `http-server` (Alternativa)

#### Instalação Global

```bash
npm install -g http-server
```

#### Iniciar o Servidor

```bash
http-server dist -p 5173 -a 0.0.0.0
```

**Parâmetros:**
- `dist`: Pasta a ser servida
- `-p 5173`: Porta 5173
- `-a 0.0.0.0`: Aceita conexões de qualquer IP

---

### Opção 3: Usando Nginx (Recomendado para produção real)

#### Instalação do Nginx

**Windows:**
- Download: https://nginx.org/en/download.html
- Extraia e execute `nginx.exe`

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install nginx
```

**Linux (CentOS/RHEL):**
```bash
sudo yum install nginx
```

#### Configuração do Nginx

Edite o arquivo de configuração (geralmente em `/etc/nginx/sites-available/default` ou `C:\nginx\conf\nginx.conf`):

```nginx
server {
    listen 80;
    server_name seu-dominio.com;  # ou seu IP

    root /caminho/para/projeto/dist;  # Caminho absoluto para a pasta dist
    index index.html;

    # Configuração para SPA (React Router)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache para assets estáticos
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;
}
```

**Windows - Exemplo de caminho:**
```nginx
root C:/Users/paulo/Desktop/Cursor Ai/SSM/SSM 3.0/Frontend/dist;
```

**Linux - Exemplo de caminho:**
```nginx
root /var/www/ssm-frontend/dist;
```

#### Iniciar/Reiniciar Nginx

**Windows:**
```bash
# Iniciar
nginx.exe

# Parar
nginx.exe -s stop

# Recarregar configuração
nginx.exe -s reload
```

**Linux:**
```bash
# Iniciar
sudo systemctl start nginx

# Habilitar no boot
sudo systemctl enable nginx

# Reiniciar
sudo systemctl restart nginx

# Verificar status
sudo systemctl status nginx
```

---

### Opção 4: Usando Apache (Alternativa)

#### Instalação do Apache

**Windows:**
- Download: https://httpd.apache.org/download.cgi
- Ou use XAMPP: https://www.apachefriends.org/

**Linux (Ubuntu/Debian):**
```bash
sudo apt install apache2
```

#### Configuração do Apache

Edite o arquivo de configuração (geralmente `/etc/apache2/sites-available/000-default.conf`):

```apache
<VirtualHost *:80>
    ServerName seu-dominio.com
    DocumentRoot /caminho/para/projeto/dist

    <Directory /caminho/para/projeto/dist>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    # Configuração para SPA (React Router)
    <IfModule mod_rewrite.c>
        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\.html$ - [L]
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /index.html [L]
    </IfModule>
</VirtualHost>
```

#### Habilitar mod_rewrite (Linux)

```bash
sudo a2enmod rewrite
sudo systemctl restart apache2
```

---

### Opção 5: Usando PM2 (Para manter o servidor rodando)

PM2 é útil para manter o processo rodando e reiniciar automaticamente.

#### Instalação

```bash
npm install -g pm2
```

#### Criar arquivo `ecosystem.config.js` na raiz do projeto:

```javascript
module.exports = {
  apps: [{
    name: 'ssm-frontend',
    script: 'serve',
    args: '-s dist -l 5173',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production'
    }
  }]
};
```

**Nota:** Você precisará ter `serve` instalado globalmente ou localmente.

#### Iniciar com PM2

```bash
pm2 start ecosystem.config.js
```

#### Comandos úteis do PM2

```bash
# Ver status
pm2 status

# Ver logs
pm2 logs ssm-frontend

# Parar
pm2 stop ssm-frontend

# Reiniciar
pm2 restart ssm-frontend

# Remover
pm2 delete ssm-frontend

# Salvar configuração para iniciar no boot
pm2 save
pm2 startup
```

---

## ⚙️ Configuração para Produção

### 1. Atualizar `src/config.json`

Antes de fazer o build, certifique-se de que o `src/config.json` está configurado para produção:

```json
{
  "backend": {
    "host": "192.168.100.3",  // IP ou domínio do backend em produção
    "port": 3000,              // Porta do backend
    "protocol": "http",        // ou "https" se usar SSL
    "basePath": "/api",
    "timeout": 60000
  },
  "frontend": {
    "port": 5173,              // Não usado em produção (apenas dev)
    "host": "0.0.0.0"          // Não usado em produção (apenas dev)
  }
}
```

**Importante:** 
- O `frontend.port` e `frontend.host` são usados apenas no modo de desenvolvimento
- Em produção, a porta é definida pelo servidor web (Nginx, Apache, etc.)

### 2. Variáveis de Ambiente (Opcional)

Você pode criar um arquivo `.env.production` na raiz:

```env
VITE_API_BASE_URL=http://192.168.100.3:3000/api
```

---

## 🔒 Configuração HTTPS (Produção Real)

Para produção real, recomenda-se usar HTTPS. Você pode usar:

### Let's Encrypt (Gratuito)

```bash
# Instalar certbot
sudo apt install certbot python3-certbot-nginx

# Obter certificado
sudo certbot --nginx -d seu-dominio.com

# Renovação automática
sudo certbot renew --dry-run
```

### Configuração Nginx com HTTPS

```nginx
server {
    listen 80;
    server_name seu-dominio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name seu-dominio.com;

    ssl_certificate /etc/letsencrypt/live/seu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu-dominio.com/privkey.pem;

    root /caminho/para/projeto/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Atualizar `src/config.json` para usar HTTPS:**

```json
{
  "backend": {
    "protocol": "https",
    "port": 443
  }
}
```

---

## 📝 Checklist de Produção

Antes de colocar em produção, verifique:

- [ ] Build executado com sucesso (`npm run build`)
- [ ] Pasta `dist/` contém todos os arquivos
- [ ] `src/config.json` configurado com IP/domínio correto do backend
- [ ] Backend está acessível e rodando
- [ ] Servidor web (Nginx/Apache) configurado corretamente
- [ ] Firewall permite conexões na porta escolhida
- [ ] Testado acesso local e externo
- [ ] HTTPS configurado (se necessário)
- [ ] Certificado SSL válido (se usar HTTPS)
- [ ] Logs do servidor verificados

---

## 🧪 Testar a Build Localmente

Antes de colocar em produção, teste a build localmente:

```bash
# Fazer build
npm run build

# Testar com preview do Vite
npm run preview

# Ou usar serve
serve -s dist -l 5173
```

Acesse `http://localhost:5173` e verifique se tudo funciona.

---

## 🔄 Atualizar Produção

Quando precisar atualizar a aplicação em produção:

1. **Fazer pull das mudanças** (se usar Git):
   ```bash
   git pull origin main
   ```

2. **Instalar dependências** (se houver novas):
   ```bash
   npm install
   ```

3. **Fazer novo build**:
   ```bash
   npm run build
   ```

4. **Reiniciar o servidor web**:
   - **Nginx**: `sudo systemctl reload nginx`
   - **Apache**: `sudo systemctl reload apache2`
   - **PM2**: `pm2 restart ssm-frontend`
   - **serve/http-server**: Parar e iniciar novamente

---

## 🐛 Troubleshooting

### Erro: "Cannot GET /route"

**Causa:** Servidor não configurado para SPA (Single Page Application).

**Solução:** Configure o servidor para redirecionar todas as rotas para `index.html` (veja configurações acima).

### Erro: "ERR_CONNECTION_REFUSED" no backend

**Causa:** Backend não está acessível ou IP/porta incorretos.

**Solução:**
- Verifique se o backend está rodando
- Confirme o IP e porta em `src/config.json`
- Teste a conexão: `curl http://[IP_BACKEND]:[PORTA]/api/server/status`

### Build muito lento

**Solução:** Normal em primeira build. Builds subsequentes são mais rápidos devido ao cache.

### Arquivos não atualizam após novo build

**Solução:**
- Limpe o cache do navegador (Ctrl + Shift + R)
- Verifique se o servidor web está servindo a pasta `dist/` correta
- Reinicie o servidor web

---

## 📞 Suporte

Para mais informações, consulte:
- [Guia de Instalação](./INSTALACAO.md)
- [Guia de Configuração](./CONFIGURACAO.md)
- [Documentação da API](./API.md)

---

**Última atualização**: 2025-01-27

