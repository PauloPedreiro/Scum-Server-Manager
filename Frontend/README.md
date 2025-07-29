# 🎮 SCUM Server Manager Frontend

Interface de administração moderna e temática para servidores do jogo SCUM.

## 🎯 Características

- **Design Temático**: Interface militar/sobrevivência inspirada no jogo SCUM
- **Autenticação Segura**: Sistema de login com JWT
- **Responsivo**: Funciona em desktop, tablet e mobile
- **Animações**: Transições suaves com Framer Motion
- **Tema Escuro**: Interface otimizada para ambientes com pouca luz

## 🚀 Tecnologias

- **React 18** + **TypeScript**
- **Vite** - Build tool rápida
- **Tailwind CSS** - Estilização utilitária
- **Framer Motion** - Animações
- **React Router** - Navegação
- **Axios** - Cliente HTTP
- **Lucide React** - Ícones

## 🎨 Tema SCUM

### Paleta de Cores
- **Primária**: Verde militar (#1a2e1a) e verde oliva (#6b8e23)
- **Secundária**: Cinza escuro (#2d2d2d) e preto (#0a0a0a)
- **Acentos**: Laranja enferrujado (#d2691e) e vermelho sangue (#8b0000)
- **Texto**: Branco sujo (#f5f5dc) e cinza claro (#d3d3d3)

### Elementos Visuais
- Bordas enferrujadas e texturas metálicas
- Efeitos de "glitch" e distorção digital
- Tipografia militar (Orbitron)
- Animações de loading e transições

## 📦 Instalação

```bash
# Instalar dependências
npm install

# Executar em desenvolvimento
npm run dev

# Build para produção
npm run build

# Preview da build
npm run preview
```

## 🔐 Autenticação

### Endpoint de Login
```
POST http://localhost:3000/api/auth/login
```

### Credenciais de Teste
- **Usuário**: `admin`
- **Senha**: `123456`

### Estrutura da Resposta
```json
{
  "success": true,
  "message": "Login realizado com sucesso",
  "data": {
    "user": {
      "id": "1",
      "username": "admin",
      "role": "admin",
      "permissions": ["read_logs", "write_logs", "manage_users"],
      "profile": {
        "firstName": "Administrador",
        "lastName": "Principal"
      }
    },
    "token": "eyJhbGciOiJIUzI1NiIs..."
  }
}
```

## 🏗️ Estrutura do Projeto

```
src/
├── components/          # Componentes reutilizáveis
├── pages/              # Páginas da aplicação
│   └── Login.tsx       # Tela de login
├── hooks/              # Hooks personalizados
│   └── useAuth.ts      # Hook de autenticação
├── services/           # Serviços de API
│   └── api.ts          # Cliente HTTP
├── types/              # Tipos TypeScript
│   └── auth.ts         # Tipos de autenticação
├── styles/             # Estilos globais
│   └── index.css       # CSS com Tailwind
├── App.tsx             # Componente principal
└── main.tsx            # Ponto de entrada
```

## 🎨 Componentes

### Login
- Formulário de autenticação temático
- Validação de campos
- Feedback visual de erros
- Animações de entrada
- Credenciais de teste visíveis

### Dashboard (Temporário)
- Layout básico com informações do servidor
- Cards de status
- Botão de logout
- Proteção de rota

## 🔧 Configuração

### Variáveis de Ambiente
```env
VITE_API_URL=http://localhost:3000
```

### Tailwind CSS
O projeto usa uma configuração personalizada do Tailwind com:
- Cores temáticas do SCUM
- Fontes militares
- Animações customizadas
- Componentes utilitários

## 🚀 Deploy

### Build para Produção
```bash
npm run build
```

### Servidor de Desenvolvimento
```bash
npm run dev
```

## 📱 Responsividade

- **Desktop**: Layout completo com sidebar
- **Tablet**: Layout adaptado
- **Mobile**: Layout otimizado para touch

## 🎯 Próximos Passos

- [ ] Dashboard completo com gráficos
- [ ] Gerenciamento de jogadores
- [ ] Configurações do servidor
- [ ] Logs em tempo real
- [ ] Sistema de notificações
- [ ] Modo offline
- [ ] PWA (Progressive Web App)

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT.

---

**Desenvolvido com ❤️ para a comunidade SCUM** 