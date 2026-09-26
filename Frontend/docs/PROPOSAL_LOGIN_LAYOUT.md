# 🎨 Proposta de Layout - Página de Login

**Data:** 2025-12-05  
**Baseado em:** Design System atual do SSM 3.0 Frontend

---

## 🎯 Princípios de Design

1. **Consistência**: Seguir padrões visuais existentes
2. **Modernidade**: Design limpo e profissional
3. **Responsividade**: Funcionar perfeitamente em mobile e desktop
4. **Acessibilidade**: Fácil de usar e entender
5. **Branding**: Destacar logo e identidade visual do SSM

---

## 🎨 Layout Proposto

### **Versão 1: Centralizado (Recomendado)**

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                    [Background Image]                   │
│                    (com blur/overlay)                   │
│                                                         │
│         ┌─────────────────────────────────┐            │
│         │                                   │            │
│         │        [Logo SSM Animado]         │            │
│         │                                   │            │
│         │    SCUM Server Manager 3.0        │            │
│         │                                   │            │
│         │  ┌───────────────────────────┐   │            │
│         │  │                           │   │            │
│         │  │    Username: [_______]    │   │            │
│         │  │    Password: [_______]     │   │            │
│         │  │                           │   │            │
│         │  │    [    Entrar    ]       │   │            │
│         │  │                           │   │            │
│         │  │  [Mensagem de erro]       │   │            │
│         │  │                           │   │            │
│         │  └───────────────────────────┘   │            │
│         │                                   │            │
│         └─────────────────────────────────┘            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Características:**
- Card centralizado vertical e horizontalmente
- Logo no topo do card
- Formulário limpo e focado
- Background com imagem (se configurado) ou gradiente escuro
- Overlay escuro para melhor contraste

---

### **Versão 2: Split Screen (Alternativa)**

```
┌──────────────────────┬──────────────────────┐
│                      │                      │
│   [Background        │  ┌────────────────┐  │
│    Image/Pattern]    │  │                │  │
│                      │  │  [Logo SSM]    │  │
│                      │  │                │  │
│                      │  │  Login Form    │  │
│                      │  │                │  │
│                      │  └────────────────┘  │
│                      │                      │
└──────────────────────┴──────────────────────┘
```

**Características:**
- Lado esquerdo: Background visual
- Lado direito: Card de login
- Melhor para telas grandes
- Mais impacto visual

---

## 🎨 Especificações Técnicas

### **Cores e Estilos**

```css
/* Container Principal */
- Background: bg-scum-bg (#0b0e13) ou background image
- Overlay: bg-black/60 (se tiver background image)

/* Card de Login */
- Background: bg-scum-panel/90 backdrop-blur-md
- Border: border border-white/10
- Border Radius: rounded-2xl
- Shadow: shadow-2xl
- Padding: p-8 md:p-10 lg:p-12

/* Inputs */
- Background: bg-black/30
- Border: border border-white/10
- Focus: border-scum-orange ring-2 ring-scum-orange/20
- Text: text-white placeholder-white/40
- Padding: px-4 py-3

/* Botão */
- Background: bg-scum-orange hover:bg-scum-orange/90
- Text: text-white font-semibold
- Padding: px-6 py-3
- Border Radius: rounded-lg
- Transition: transition-all duration-200
```

### **Estrutura HTML/JSX**

```tsx
<div className="min-h-screen flex items-center justify-center p-4">
  {/* Background com overlay */}
  <div className="absolute inset-0 bg-scum-bg">
    {/* Background image se configurado */}
    <div className="absolute inset-0 bg-black/60" />
  </div>

  {/* Card de Login */}
  <div className="relative z-10 w-full max-w-md">
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="card p-8 md:p-10"
    >
      {/* Logo */}
      <div className="text-center mb-8">
        <motion.img
          src={SsmLogo}
          alt="SSM"
          className="h-16 w-16 mx-auto mb-4"
          animate={{ scale: [1, 1.05, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
        <h1 className="text-2xl font-bold text-white">
          SCUM Server Manager
        </h1>
        <p className="text-white/60 mt-2">Faça login para continuar</p>
      </div>

      {/* Formulário */}
      <form onSubmit={handleLogin}>
        {/* Inputs */}
        {/* Botão */}
        {/* Mensagens de erro */}
      </form>
    </motion.div>
  </div>
</div>
```

---

## 📱 Responsividade

### **Mobile (< 640px)**
- Card ocupa quase toda a largura (margem de 16px)
- Padding reduzido (p-6)
- Logo menor (h-12 w-12)
- Inputs full width

### **Tablet (640px - 768px)**
- Card com largura máxima de 400px
- Padding médio (p-8)
- Logo médio (h-14 w-14)

### **Desktop (> 768px)**
- Card com largura máxima de 450px
- Padding maior (p-10)
- Logo grande (h-16 w-16)
- Espaçamento generoso

---

## ✨ Animações Propostas

### **1. Entrada do Card**
```tsx
<motion.div
  initial={{ opacity: 0, y: 20, scale: 0.95 }}
  animate={{ opacity: 1, y: 0, scale: 1 }}
  transition={{ duration: 0.4, ease: "easeOut" }}
>
```

### **2. Logo Pulsante**
```tsx
<motion.img
  animate={{ scale: [1, 1.05, 1] }}
  transition={{ duration: 2, repeat: Infinity }}
/>
```

### **3. Input Focus**
```tsx
// Transição suave ao focar
className="transition-all duration-200 focus:ring-2 focus:ring-scum-orange/20"
```

### **4. Botão Loading**
```tsx
// Spinner animado durante loading
{loading && <Loader2 className="animate-spin" />}
```

---

## 🎨 Elementos Visuais

### **Logo**
- Logo SSM animado (GIF) no topo
- Tamanho: 64px (mobile) a 80px (desktop)
- Animação sutil de pulsação
- Centralizado

### **Título**
- "SCUM Server Manager" ou "SSM 3.0"
- Fonte: bold, tamanho responsivo
- Cor: text-white

### **Subtítulo**
- "Faça login para continuar" / "Login to continue"
- Cor: text-white/60
- Tamanho menor que o título

### **Inputs**
- Ícones à esquerda (User, Lock)
- Placeholder claro
- Validação visual (borda verde/vermelha)
- Mensagens de erro abaixo de cada input

### **Botão**
- Cor laranja (scum-orange)
- Full width no mobile
- Hover effect (escala ou brilho)
- Estado disabled quando loading

### **Mensagens de Erro**
- Card vermelho sutil
- Ícone de alerta
- Texto claro e objetivo
- Animação de entrada

---

## 🔐 Tela de Mudança de Senha

Layout similar ao login, mas com:

1. **Título diferente**: "Alterar Senha Obrigatória"
2. **Mensagem informativa**: "Por favor, altere sua senha padrão"
3. **3 inputs**: Senha Atual, Nova Senha, Confirmar Senha
4. **Validação visual**: Indicador de força da senha
5. **Mesmo estilo visual**: Consistência com login

---

## 📐 Medidas e Espaçamentos

```
Card:
- Max Width: 450px (desktop), 100% - 32px (mobile)
- Padding: 32px (mobile), 40px (tablet), 48px (desktop)
- Border Radius: 16px (rounded-2xl)
- Gap entre elementos: 24px

Inputs:
- Height: 44px
- Padding: 12px 16px
- Border Radius: 8px (rounded-lg)
- Gap entre label e input: 8px

Botão:
- Height: 44px
- Padding: 12px 24px
- Border Radius: 8px
- Margin top: 24px
```

---

## 🎯 Variações de Design

### **Opção A: Minimalista (Recomendado)**
- Card simples e limpo
- Foco no formulário
- Background sutil
- **Melhor para**: Foco na funcionalidade

### **Opção B: Visual Impactante**
- Background com imagem do jogo
- Card com glassmorphism forte
- Animações mais elaboradas
- **Melhor para**: Primeira impressão

### **Opção C: Profissional Corporativo**
- Design mais sóbrio
- Cores mais neutras
- Tipografia destacada
- **Melhor para**: Ambiente corporativo

---

## ✅ Checklist de Implementação

### **Estrutura**
- [ ] Container principal com background
- [ ] Card centralizado responsivo
- [ ] Logo e título
- [ ] Formulário com inputs
- [ ] Botão de submit
- [ ] Área de mensagens de erro

### **Estilos**
- [ ] Aplicar cores do tema SCUM
- [ ] Usar classes Tailwind existentes
- [ ] Responsividade mobile-first
- [ ] Estados de hover/focus
- [ ] Estados de loading/disabled

### **Animações**
- [ ] Animação de entrada do card
- [ ] Animação do logo
- [ ] Transições suaves
- [ ] Feedback visual de erros

### **Funcionalidade**
- [ ] Validação de formulário
- [ ] Mensagens de erro
- [ ] Estado de loading
- [ ] Integração com serviço de auth
- [ ] Redirecionamento após login

### **Acessibilidade**
- [ ] Labels para inputs
- [ ] ARIA labels
- [ ] Navegação por teclado
- [ ] Foco visível
- [ ] Contraste adequado

---

## 🎨 Exemplo de Código Completo

```tsx
import { motion } from 'framer-motion';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { User, Lock, Loader2, AlertCircle } from 'lucide-react';
import SsmLogo from '@/assets/logo/logoSSM.gif';
import { authService } from '@/services/auth';
import { useNavigate } from 'react-router-dom';

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await authService.login(username, password);
      
      if (response.success) {
        if (response.data?.must_change_password) {
          navigate('/change-password', {
            state: { username, currentPassword: password }
          });
        } else {
          navigate('/');
        }
      } else {
        setError(response.error || t('auth.login.errors.invalidCredentials'));
      }
    } catch (err) {
      setError(t('auth.login.errors.networkError'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative">
      {/* Background */}
      <div className="absolute inset-0 bg-scum-bg">
        <div className="absolute inset-0 bg-black/60" />
      </div>

      {/* Card de Login */}
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="relative z-10 w-full max-w-md"
      >
        <div className="card p-8 md:p-10">
          {/* Logo e Título */}
          <div className="text-center mb-8">
            <motion.img
              src={SsmLogo}
              alt="SSM"
              className="h-16 w-16 mx-auto mb-4"
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            <h1 className="text-2xl font-bold text-white mb-2">
              {t('app.title')}
            </h1>
            <p className="text-white/60 text-sm">
              {t('auth.login.subtitle')}
            </p>
          </div>

          {/* Formulário */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div>
              <label className="block text-sm font-medium text-white/80 mb-2">
                {t('auth.login.username')}
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={20} />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-black/30 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-scum-orange transition-all"
                  placeholder={t('auth.login.usernamePlaceholder')}
                  required
                  disabled={loading}
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-white/80 mb-2">
                {t('auth.login.password')}
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={20} />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-black/30 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-scum-orange transition-all"
                  placeholder={t('auth.login.passwordPlaceholder')}
                  required
                  disabled={loading}
                />
              </div>
            </div>

            {/* Mensagem de Erro */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm"
              >
                <AlertCircle size={16} />
                <span>{error}</span>
              </motion.div>
            )}

            {/* Botão */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-scum-orange hover:bg-scum-orange/90 text-white font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  <span>{t('auth.login.loading')}</span>
                </>
              ) : (
                <span>{t('auth.login.submit')}</span>
              )}
            </button>
          </form>
        </div>
      </motion.div>
    </div>
  );
}
```

---

## 🎯 Recomendação Final

**Sugiro a Versão 1 (Centralizado)** porque:

1. ✅ **Consistente** com o design atual
2. ✅ **Responsivo** e funciona bem em todos os dispositivos
3. ✅ **Focado** na funcionalidade principal
4. ✅ **Familiar** para usuários (padrão comum)
5. ✅ **Fácil de implementar** e manter

**Variação recomendada**: Opção A (Minimalista) com:
- Background escuro sólido ou com blur sutil
- Card com glassmorphism moderado
- Animações suaves e profissionais
- Foco na experiência do usuário

---

**Próximo passo**: Implementar seguindo esta proposta ou ajustar conforme feedback.

