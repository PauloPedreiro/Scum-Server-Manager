# 🎯 Planejamento: Implementação Steam Community XML API para Novos Jogadores

## 📋 Objetivo

Implementar sistema para obter informações de novos jogadores via **Steam Community XML API** (sem API key), focando apenas nos dados essenciais para notificações no Discord.

---

## 🎯 Campos que Vamos Usar

### ✅ Dados Essenciais (Apenas 4 campos)

1. **Nome do Jogador** - `<steamID>`
2. **Avatar Completo** - `<avatarFull>`
3. **País** - `<countryCode>` ou `<location>`
4. **Link do Perfil** - Construído a partir do `steamID64`

### ❌ Campos que NÃO vamos usar

- VAC ban status
- Grupos
- Amigos
- Biografia
- Nome real
- Data de criação
- Status online
- Qualquer outro campo extra

---

## 🔍 Análise do Problema Atual

### Problema Identificado

1. **Método `_get_steam_community_info()` não existe**
   - Código chama método que não foi implementado
   - Causa `AttributeError` silencioso
   - Resultado: "Unknown Player" no Discord

2. **Sistema tenta usar API key oficial**
   - Não é necessário
   - Adiciona complexidade desnecessária
   - Risco de segurança

### Solução Proposta

**Sempre usar Steam Community XML API** como método principal, sem dependência de API key.

---

## 🏗️ Arquitetura da Solução

### Fluxo Simplificado

```
1. Novo jogador detectado
   ↓
2. Chamar get_player_info(steam_id)
   ↓
3. Consultar Steam Community XML API
   http://steamcommunity.com/profiles/{steamid}/?xml=1
   ↓
4. Extrair apenas 4 campos essenciais
   - steamID (nome)
   - avatarFull (avatar)
   - countryCode (país)
   - steamID64 (para link)
   ↓
5. Formatar dados para Discord
   ↓
6. Enviar notificação
```

---

## 📝 Implementação Detalhada

### Fase 1: Implementar `_get_steam_community_info()`

**Arquivo:** `core/logs/steam_api.py`

**Constantes de Segurança (Hardcoded):**
```python
# No topo do arquivo steam_api.py (hardcoded para segurança)
STEAM_COMMUNITY_XML_BASE_URL = "http://steamcommunity.com/profiles"
STEAM_COMMUNITY_XML_SUFFIX = "/?xml=1"
STEAM_PROFILE_BASE_URL = "https://steamcommunity.com/profiles"
```

**Método a implementar:**
```python
def _validate_steam_id(self, steam_id: str) -> bool:
    """
    Validar formato do Steam ID (segurança)
    
    Args:
        steam_id: Steam ID a validar
        
    Returns:
        True se válido, False caso contrário
    """
    if not steam_id:
        return False
    # Steam ID deve conter apenas números
    if not steam_id.isdigit():
        return False
    # Steam ID64 tem entre 17 e 19 dígitos
    if len(steam_id) < 17 or len(steam_id) > 19:
        return False
    return True

def _get_steam_community_info(self, steam_id: str) -> Dict[str, Any]:
    """
    Obter informações do jogador via Steam Community XML API
    
    Retorna apenas dados essenciais:
    - Nome (steamID)
    - Avatar (avatarFull)
    - País (countryCode ou location)
    - Link do perfil (construído)
    
    Args:
        steam_id: Steam ID do jogador (64-bit)
        
    Returns:
        Dict com informações essenciais do jogador
    """
    # VALIDAÇÃO DE SEGURANÇA: Validar Steam ID antes de usar
    if not self._validate_steam_id(steam_id):
        print(f"ERRO: Steam ID inválido: {steam_id}")
        return self._get_fallback_info(steam_id)
    
    # CONSTRUÇÃO SEGURA: Usar constantes hardcoded + steam_id validado
    xml_url = f"{STEAM_COMMUNITY_XML_BASE_URL}/{steam_id}{STEAM_COMMUNITY_XML_SUFFIX}"
    # Nunca fazer: f"http://{user_input}/..." ou construir URL dinamicamente sem validação
```

**Campos a extrair do XML:**
```python
{
    'steam_id': steam_id,                    # Steam ID64 (já validado)
    'persona_name': root.findtext('steamID'), # Nome do jogador
    'avatar_full_url': root.findtext('avatarFull'), # Avatar completo
    'country_code': root.findtext('countryCode', ''), # Código do país
    'location': root.findtext('location', ''), # Localização completa (fallback)
    'profile_url': f"{STEAM_PROFILE_BASE_URL}/{steam_id}" # Link do perfil (hardcoded base)
}
```

**⚠️ Importante - Segurança:**
- ✅ Steam ID é validado antes de construir URL
- ✅ URLs são hardcoded (não podem ser modificadas)
- ✅ Nunca aceitar URLs de fontes externas
- ✅ Sempre usar constantes para bases de URL

**Tratamento de erros:**
- Perfil privado → Retornar dados disponíveis (pelo menos nome)
- Perfil não encontrado → Retornar fallback
- Erro de rede → Retornar fallback
- XML inválido → Retornar fallback

---

### Fase 2: Refatorar `get_player_info()`

**Arquivo:** `core/logs/steam_api.py`

**Mudanças:**
1. **Remover dependência de API key**
2. **Sempre usar Steam Community XML API primeiro**
3. **Simplificar lógica** (sem fallback para API oficial)

**Código proposto:**
```python
def get_player_info(self, steam_id: str) -> Dict[str, Any]:
    """
    Obter informações do jogador via Steam Community XML API
    
    Args:
        steam_id: Steam ID do jogador
        
    Returns:
        Dict com informações do jogador
    """
    try:
        # Verificar cache primeiro
        cache_key = f"player_{steam_id}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now().timestamp() - timestamp < self.cache_timeout:
                return cached_data
        
        # SEMPRE usar Steam Community XML API
        player_info = self._get_steam_community_info(steam_id)
        
        # Salvar no cache
        self.cache[cache_key] = (player_info, datetime.now().timestamp())
        
        return player_info
                
    except Exception as e:
        print(f"ERRO: Erro ao obter dados do jogador: {e}")
        return self._get_fallback_info(steam_id)
```

---

### Fase 3: Atualizar `format_player_info()`

**Arquivo:** `core/logs/steam_api.py`

**Mudanças:**
- Formatar apenas os 4 campos essenciais
- Priorizar `countryCode`, usar `location` como fallback
- Garantir que avatar sempre tenha URL válida

**Código proposto:**
```python
def format_player_info(self, player_info: Dict[str, Any]) -> Dict[str, str]:
    """
    Formatar informações do jogador para exibição no Discord
    
    Retorna apenas dados essenciais:
    - persona_name (nome)
    - avatar_url (avatar completo)
    - country (país formatado)
    - profile_url (link do perfil)
    """
    # Obter país (priorizar countryCode, fallback para location)
    country_code = player_info.get('country_code', '')
    location = player_info.get('location', '')
    
    # Formatar país
    if country_code:
        country_flag = self.get_country_flag(country_code)
        country_name = self._get_country_name(country_code)
        country = f"{country_flag} {country_name}"
    elif location:
        country = f"🌍 {location}"
    else:
        country = "🌍 Unknown"
    
    # Garantir avatar (usar fallback se vazio)
    avatar_url = player_info.get('avatar_full_url', '')
    if not avatar_url:
        # Tentar avatar médio como fallback
        avatar_url = player_info.get('avatar_medium_url', '')
    
    return {
        'steam_id': player_info.get('steam_id', ''),
        'persona_name': player_info.get('persona_name', 'Unknown Player'),
        'avatar_url': avatar_url,
        'country': country,
        'profile_url': player_info.get('profile_url', f"https://steamcommunity.com/profiles/{player_info.get('steam_id', '')}")
    }
```

---

### Fase 4: Atualizar `_send_new_player_notification()`

**Arquivo:** `core/logs/player_processor.py`

**Mudanças:**
- Usar apenas os 4 campos essenciais
- Remover campos desnecessários do embed
- Simplificar estrutura

**Campos do embed Discord:**
```python
embed = {
    "title": "🎉 New Player on Server!",
    "color": 0xFF6B35,  # Laranja
    "fields": [
        {
            "name": "In-Game Name",
            "value": player_name,  # Nome do jogo
            "inline": True
        },
        {
            "name": "Steam Name",
            "value": steam_name,  # Nome Steam (de steam_info)
            "inline": True
        },
        {
            "name": "Steam ID",
            "value": f"`{steam_id}`",
            "inline": True
        },
        {
            "name": "Country",
            "value": country,  # País formatado (de steam_info)
            "inline": True
        },
        {
            "name": "🔗 Steam Profile",
            "value": f"[Click here]({steam_profile_url})",  # Link do perfil
            "inline": False
        }
    ],
    "thumbnail": {
        "url": avatar_url  # Avatar completo (de steam_info)
    },
    "footer": {
        "text": "SCUM Server Manager"
    }
}
```

---

## 🔒 Medidas de Segurança

### 1. Hardcode de URLs (Recomendado)

**Por que hardcode?**
- ✅ Previne injeção de URL maliciosa
- ✅ Garante uso apenas do endpoint oficial da Steam
- ✅ Não pode ser modificado em runtime
- ✅ Mais fácil de auditar e verificar

**Implementação:**
```python
# Constantes no topo do arquivo (hardcoded)
STEAM_COMMUNITY_XML_BASE_URL = "http://steamcommunity.com/profiles"
STEAM_COMMUNITY_XML_SUFFIX = "/?xml=1"
STEAM_PROFILE_BASE_URL = "https://steamcommunity.com/profiles"

# Uso seguro
def _get_steam_community_info(self, steam_id: str) -> Dict[str, Any]:
    # Validar steam_id (apenas números)
    if not steam_id or not steam_id.isdigit():
        return self._get_fallback_info(steam_id)
    
    # Construir URL de forma segura
    xml_url = f"{STEAM_COMMUNITY_XML_BASE_URL}/{steam_id}{STEAM_COMMUNITY_XML_SUFFIX}"
    # Nunca usar: f"http://steamcommunity.com/profiles/{steam_id}/?xml=1" diretamente
```

### 2. Validação de Steam ID

**Validações necessárias:**
- ✅ Apenas números (não aceitar caracteres especiais)
- ✅ Comprimento mínimo/máximo
- ✅ Não vazio

**Código:**
```python
def _validate_steam_id(self, steam_id: str) -> bool:
    """Validar formato do Steam ID"""
    if not steam_id:
        return False
    if not steam_id.isdigit():
        return False
    if len(steam_id) < 17 or len(steam_id) > 19:
        return False
    return True
```

### 3. Timeout e Rate Limiting

**Proteções:**
- ✅ Timeout de 10 segundos nas requisições
- ✅ Cache de 5 minutos (reduz requisições)
- ✅ Tratamento de erros de rede

---

## 🔧 Detalhes Técnicos

### Segurança: Hardcode de URLs

**Benefícios:**
- ✅ Previne injeção de URL maliciosa
- ✅ Garante que sempre usa endpoint oficial
- ✅ Não pode ser modificado em runtime
- ✅ Mais fácil de auditar

**Constantes definidas:**
```python
# No topo do arquivo steam_api.py
STEAM_COMMUNITY_XML_BASE_URL = "http://steamcommunity.com/profiles"
STEAM_COMMUNITY_XML_SUFFIX = "/?xml=1"
STEAM_PROFILE_BASE_URL = "https://steamcommunity.com/profiles"
```

**Validação de Steam ID:**
```python
# Validar que steam_id contém apenas números
if not steam_id or not steam_id.isdigit():
    raise ValueError(f"Steam ID inválido: {steam_id}")
```

### Parsing XML

**Biblioteca:** `xml.etree.ElementTree` (padrão Python, sem dependências extras)

**Exemplo:**
```python
import xml.etree.ElementTree as ET

# URL construída de forma segura (hardcoded base + steam_id validado)
xml_url = f"{STEAM_COMMUNITY_XML_BASE_URL}/{steam_id}{STEAM_COMMUNITY_XML_SUFFIX}"

response = requests.get(xml_url, timeout=10)
root = ET.fromstring(response.content)

# Extrair campos
nome = root.findtext('steamID', 'Unknown Player')
avatar = root.findtext('avatarFull', '')
pais = root.findtext('countryCode', '')
localizacao = root.findtext('location', '')
```

### Cache Strategy

- **Duração:** 5 minutos (300 segundos)
- **Chave:** `player_{steam_id}`
- **Benefício:** Reduz requisições desnecessárias

### Tratamento de Erros

**Cenários:**
1. **Perfil privado** → Retorna nome (se disponível), avatar padrão
2. **Perfil não encontrado** → Retorna fallback completo
3. **Erro de rede** → Retorna fallback completo
4. **XML inválido** → Retorna fallback completo
5. **Timeout** → Retorna fallback completo

**Fallback:**
```python
{
    'steam_id': steam_id,
    'persona_name': 'Unknown Player',
    'avatar_full_url': '',
    'country_code': '',
    'location': '',
    'profile_url': f"https://steamcommunity.com/profiles/{steam_id}"
}
```

---

## 📦 Dependências

### ✅ Nenhuma Nova Dependência!

Usa apenas bibliotecas padrão do Python:
- `xml.etree.ElementTree` - Parsing XML (já incluído)
- `requests` - Já está no `requirements.txt`

---

## ✅ Checklist de Implementação

### Fase 1: Implementar `_get_steam_community_info()`
- [ ] Criar método que consulta XML API
- [ ] Extrair apenas 4 campos essenciais
- [ ] Implementar tratamento de erros
- [ ] Adicionar cache
- [ ] Testar com Steam ID válido
- [ ] Testar com perfil privado
- [ ] Testar com Steam ID inválido

### Fase 2: Refatorar `get_player_info()`
- [ ] Remover dependência de API key
- [ ] Sempre usar XML API primeiro
- [ ] Simplificar lógica
- [ ] Testar fluxo completo

### Fase 3: Atualizar `format_player_info()`
- [ ] Formatar apenas 4 campos essenciais
- [ ] Priorizar countryCode sobre location
- [ ] Garantir fallback de avatar
- [ ] Testar formatação

### Fase 4: Atualizar `_send_new_player_notification()`
- [ ] Usar apenas dados essenciais
- [ ] Simplificar embed do Discord
- [ ] Testar notificação no Discord
- [ ] Verificar se avatar aparece
- [ ] Verificar se nome aparece
- [ ] Verificar se país aparece
- [ ] Verificar se link funciona

### Testes Finais
- [ ] Testar com novo jogador real
- [ ] Verificar notificação no Discord
- [ ] Verificar cache funcionando
- [ ] Verificar tratamento de erros
- [ ] Verificar performance

---

## 🎯 Resultado Esperado

### Notificação no Discord

```
🎉 New Player on Server!

In-Game Name: Kill
Steam Name: KillPlayer
Steam ID: 76561199734658327
Country: 🇧🇷 Brazil

🔗 Steam Profile: [Click here]

[Avatar do jogador como thumbnail]
```

### Dados Obtidos

```python
{
    'steam_id': '76561199734658327',
    'persona_name': 'KillPlayer',
    'avatar_full_url': 'https://avatars.steamstatic.com/...full.jpg',
    'country_code': 'BR',
    'location': 'Brasil, São Paulo',
    'profile_url': 'https://steamcommunity.com/profiles/76561199734658327'
}
```

---

## 🚀 Ordem de Execução

1. **Fase 1** - Implementar `_get_steam_community_info()` (crítico)
2. **Fase 2** - Refatorar `get_player_info()` (crítico)
3. **Fase 3** - Atualizar `format_player_info()` (importante)
4. **Fase 4** - Atualizar `_send_new_player_notification()` (importante)
5. **Testes** - Validar tudo funcionando

---

## 📝 Notas Importantes

### Medidas de Segurança Implementadas

1. **URLs Hardcoded** ✅
   - Constantes no código (não podem ser modificadas)
   - Previne injeção de URL maliciosa
   - Garante uso apenas de endpoints oficiais

2. **Validação de Steam ID** ✅
   - Apenas números permitidos
   - Comprimento validado (17-19 dígitos)
   - Rejeita entradas inválidas antes de fazer requisição

3. **Construção Segura de URLs** ✅
   - Base URL hardcoded
   - Steam ID validado antes de concatenar
   - Nunca construir URL a partir de input não validado

### Simplificações

1. **Removemos dependência de API key** - Mais seguro e simples
2. **Apenas 4 campos** - Foco no essencial
3. **Sem VAC ban check** - Não necessário para o projeto
4. **Sem dados extras** - Mantém código limpo

### Vantagens

- ✅ **Segurança**: 
  - Sem API key = sem risco de exposição
  - URLs hardcoded = sem risco de injeção
  - Validação de input = previne ataques
- ✅ **Simplicidade**: Código mais limpo e fácil de manter
- ✅ **Performance**: Menos dados = mais rápido
- ✅ **Confiabilidade**: Endpoint oficial e estável

### Limitações Aceitas

- ⚠️ Perfis privados podem ter dados limitados (mas nome geralmente disponível)
- ⚠️ País pode não estar disponível em perfis privados
- ⚠️ Avatar pode não estar disponível em perfis privados

**Solução:** Sempre ter fallback para "Unknown Player" e avatar vazio.

---

## 🔄 Próximos Passos

1. ✅ Planejamento completo (este documento)
2. Implementar Fase 1 (`_get_steam_community_info()`)
3. Implementar Fase 2 (refatorar `get_player_info()`)
4. Implementar Fase 3 (atualizar `format_player_info()`)
5. Implementar Fase 4 (atualizar notificação)
6. Testar tudo
7. Deploy

---

**Status:** ✅ Planejamento Completo  
**Próximo passo:** Implementação da Fase 1

