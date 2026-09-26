# 📋 Campos Completos do XML de Perfil Steam

## 🔍 Lista Completa de Campos Retornados

Quando você acessa `http://steamcommunity.com/profiles/{steamid}/?xml=1`, o XML retorna os seguintes campos:

---

## 📊 Campos Principais (Já Mencionados)

### Identificação
- **`<steamID64>`** - Steam ID numérico (64-bit)
- **`<steamID>`** - Nome de exibição do jogador
- **`<customURL>`** - URL personalizada do perfil (se configurada)

### Avatar
- **`<avatarIcon>`** - URL do avatar pequeno (32x32px)
- **`<avatarMedium>`** - URL do avatar médio (64x64px)
- **`<avatarFull>`** - URL do avatar completo (184x184px)

### Status Online
- **`<onlineState>`** - Estado online: `online`, `offline`, `in-game`
- **`<stateMessage>`** - Mensagem de status (ex: "Em jogo: SCUM")

### Privacidade
- **`<privacyState>`** - Estado de privacidade: `public`, `friends`, `private`
- **`<visibilityState>`** - Estado de visibilidade: `1` (público), `3` (privado)

### Bans e Restrições
- **`<vacBanned>`** - Status VAC ban: `0` (não banido), `1` (banido)
- **`<tradeBanState>`** - Estado de ban de trade: `None`, `Limited`, `Banned`
- **`<isLimitedAccount>`** - Conta limitada: `0` (não), `1` (sim)

---

## 📍 Campos de Localização (O "E mais")

### Localização Geográfica
- **`<location>`** - Localização completa (ex: "Brasil, São Paulo")
- **`<countryCode>`** - Código do país (ex: `BR`, `US`, `DE`)
- **`<stateCode>`** - Código do estado/província (se disponível)
- **`<cityID>`** - ID da cidade no sistema Steam (se disponível)

**Exemplo:**
```xml
<location>Brasil, São Paulo</location>
<countryCode>BR</countryCode>
<stateCode>SP</stateCode>
<cityID>12345</cityID>
```

---

## 👤 Informações Pessoais

### Dados do Perfil
- **`<realname>`** - Nome real do jogador (se público e configurado)
- **`<summary>`** - Biografia/resumo do perfil (texto livre)
- **`<headline>`** - Headline/frase do perfil (texto curto)

**Exemplo:**
```xml
<realname>João Silva</realname>
<summary>Jogador de SCUM desde 2020. Adoro survival games!</summary>
<headline>Survivor</headline>
```

---

## 📅 Informações de Conta

### Data e Tempo
- **`<memberSince>`** - Data de criação da conta Steam (formato: "Jan 1, 2015")

**Exemplo:**
```xml
<memberSince>Jan 15, 2018</memberSince>
```

---

## 🎮 Informações de Jogos

### Status em Jogo
- **`<inGameServerIP>`** - IP do servidor atual (se em jogo)
- **`<inGameServerName>`** - Nome do servidor atual (se em jogo)

**Exemplo:**
```xml
<inGameServerIP>192.168.1.100:7777</inGameServerIP>
<inGameServerName>SCUM Server #1</inGameServerName>
```

---

## 👥 Informações Sociais

### Grupos
- **`<groups>`** - Lista de grupos que o jogador participa
  - Contém sub-elementos `<group>` com informações de cada grupo

**Exemplo:**
```xml
<groups>
    <group>
        <groupID64>123456789</groupID64>
        <groupName>SCUM Brasil</groupName>
        <groupURL>scum-brasil</groupURL>
    </group>
</groups>
```

### Amigos
- **`<friends>`** - Lista de amigos (se perfil público)
  - Contém sub-elementos `<friend>` com informações de cada amigo

**Exemplo:**
```xml
<friends>
    <friend>
        <steamID64>76561198000000001</steamID64>
        <steamID>Amigo1</steamID>
        <relationship>friend</relationship>
        <friendSince>1234567890</friendSince>
    </friend>
</friends>
```

---

## 🏆 Informações de Nível e Badges

### Nível Steam
- **`<steamLevel>`** - Nível da conta Steam (se disponível)

**Exemplo:**
```xml
<steamLevel>42</steamLevel>
```

### Badges
- **`<badges>`** - Lista de badges/emblemas coletados
  - Contém sub-elementos `<badge>` com informações de cada badge

---

## 💰 Informações de Inventário

### Valor do Inventário
- **`<inventoryValue>`** - Valor estimado do inventário (se disponível)

---

## 📊 Estatísticas Adicionais

### Tempo de Jogo
- **`<hoursPlayed2Wk>`** - Horas jogadas nas últimas 2 semanas (se público)

### Jogos Favoritos
- **`<favoriteGame>`** - Jogo favorito (se configurado)
  - Contém informações sobre o jogo favorito

---

## 🔒 Campos de Segurança

### Verificações
- **`<isLimitedAccount>`** - Conta limitada (não gastou $5 na Steam)
- **`<hasMobileAuth>`** - Tem autenticação móvel ativada (se disponível)

---

## 📝 Campos de Conteúdo

### Comentários
- **`<comments>`** - Comentários públicos do perfil (se disponível)
  - Contém sub-elementos `<comment>` com comentários recentes

### Screenshots
- **`<screenshots>`** - Screenshots públicas (se disponível)

---

## 🎨 Campos de Personalização

### Tema do Perfil
- **`<profileTheme>`** - Tema do perfil (se personalizado)

### Background
- **`<profileBackground>`** - Imagem de fundo do perfil (se personalizada)

---

## ⚠️ Campos Condicionais

### Disponibilidade
Muitos campos podem estar **vazios** ou **não presentes** dependendo de:
- Configurações de privacidade do perfil
- Se o jogador configurou essas informações
- Se o perfil é público, privado ou apenas para amigos

### Exemplos de Campos que Podem Estar Vazios:
- `<realname>` - Só aparece se público
- `<location>` - Só aparece se configurado e público
- `<summary>` - Só aparece se preenchido
- `<friends>` - Só aparece se perfil público
- `<groups>` - Só aparece se perfil público

---

## 📋 Resumo para Nosso Caso de Uso

Para notificações de novos jogadores, os campos **mais úteis** são:

### ✅ Essenciais (Sempre Disponíveis)
- `<steamID>` - Nome do jogador
- `<avatarFull>` - Avatar completo
- `<steamID64>` - Steam ID numérico

### ✅ Úteis (Se Disponíveis)
- `<countryCode>` - País do jogador
- `<location>` - Localização completa
- `<memberSince>` - Quando criou a conta
- `<onlineState>` - Status online

### ❌ Não Necessários (Para Nosso Caso)
- `<vacBanned>` - Não vamos usar
- `<groups>` - Não relevante
- `<friends>` - Não relevante
- `<summary>` - Muito texto
- `<realname>` - Dados sensíveis
- `<inGameServerIP>` - Informação temporária

---

## 💡 Exemplo Completo de XML

```xml
<profile>
    <!-- Identificação -->
    <steamID64>76561198000000000</steamID64>
    <steamID>NomeDoJogador</steamID>
    <customURL>nome-personalizado</customURL>
    
    <!-- Avatar -->
    <avatarIcon>https://avatars.steamstatic.com/...icon.jpg</avatarIcon>
    <avatarMedium>https://avatars.steamstatic.com/...medium.jpg</avatarMedium>
    <avatarFull>https://avatars.steamstatic.com/...full.jpg</avatarFull>
    
    <!-- Status -->
    <onlineState>in-game</onlineState>
    <stateMessage>Em jogo: SCUM</stateMessage>
    <privacyState>public</privacyState>
    <visibilityState>1</visibilityState>
    
    <!-- Bans -->
    <vacBanned>0</vacBanned>
    <tradeBanState>None</tradeBanState>
    <isLimitedAccount>0</isLimitedAccount>
    
    <!-- Localização -->
    <location>Brasil, São Paulo</location>
    <countryCode>BR</countryCode>
    <stateCode>SP</stateCode>
    <cityID>12345</cityID>
    
    <!-- Informações Pessoais -->
    <realname>João Silva</realname>
    <summary>Jogador de SCUM desde 2020</summary>
    <headline>Survivor</headline>
    
    <!-- Conta -->
    <memberSince>Jan 15, 2018</memberSince>
    <steamLevel>42</steamLevel>
    
    <!-- Jogo Atual -->
    <inGameServerIP>192.168.1.100:7777</inGameServerIP>
    <inGameServerName>SCUM Server #1</inGameServerName>
    
    <!-- Grupos (se público) -->
    <groups>
        <group>
            <groupID64>123456789</groupID64>
            <groupName>SCUM Brasil</groupName>
        </group>
    </groups>
    
    <!-- Amigos (se público) -->
    <friends>
        <friend>
            <steamID64>76561198000000001</steamID64>
            <steamID>Amigo1</steamID>
        </friend>
    </friends>
</profile>
```

---

## 🎯 Conclusão

O "E mais" se refere a todos esses campos adicionais que podem ser úteis para outros projetos, mas para nosso caso específico (notificações de novos jogadores), vamos usar apenas:

1. **Nome** (`steamID`)
2. **Avatar** (`avatarFull`)
3. **País** (`countryCode` ou `location`)
4. **Link do perfil** (construído a partir do `steamID64`)

Todos os outros campos são opcionais e podem ser ignorados para simplificar o código.

---

**Última atualização:** 2025-01-XX

