# 🔧 Planejamento: Correção do Sistema de Steam API para Novos Jogadores

## 📋 Problema Identificado

O sistema não está conseguindo trazer o nome e a imagem do jogador nas notificações do Discord. A notificação mostra "Unknown Player" e não exibe avatar.

## 🎯 Decisão de Arquitetura: Usar Steam Community XML API (Sem API Key)

**Motivação:**
- ✅ **Segurança**: Não requer API key, eliminando riscos de exposição de credenciais
- ✅ **Simplicidade**: API pública e gratuita, sem necessidade de registro
- ✅ **Confiabilidade**: Endpoint estável mantido pela Steam
- ✅ **Dados suficientes**: Fornece nome e avatar, que são os dados necessários

**Endpoint:**
```
http://steamcommunity.com/profiles/{steamid}/?xml=1
```

**Dados retornados (XML):**
- `<steamID>` - Nome do jogador
- `<avatarFull>` - URL do avatar completo
- `<avatarMedium>` - URL do avatar médio
- `<avatarIcon>` - URL do avatar pequeno
- `<profileState>` - Estado do perfil
- `<countryCode>` - Código do país (se disponível)

## 🔍 Análise dos Problemas

### Problema 1: Método `_get_steam_community_info()` Não Implementado ⚠️ **CRÍTICO**

**Localização:** `core/logs/steam_api.py` - linha 53

**Problema:**
- O código chama `self._get_steam_community_info(steam_id)` quando não há API key
- Este método **não existe**, causando `AttributeError`
- O erro é silenciado e cai no fallback que retorna "Unknown Player"

**Código Atual:**
```python
# Se não tiver API key, usar Steam Community como fallback
if not self.api_key:
    print(f"AVISO: Steam API key não configurada para {steam_id} - usando Steam Community")
    return self._get_steam_community_info(steam_id)  # ❌ Método não existe
```

---

### Problema 2: Sistema Atual Depende de API Key ⚠️ **CRÍTICO**

**Problema:**
- O código atual tenta usar API key oficial da Steam primeiro
- Se não houver API key, deveria usar fallback, mas o método não existe
- Isso causa falha silenciosa e retorna "Unknown Player"

**Solução:**
- **Remover dependência de API key oficial**
- **Sempre usar Steam Community XML API** (mais seguro e não requer credenciais)
- Manter compatibilidade: se API key existir, ainda pode ser usada como fallback secundário

---

### Problema 3: Tratamento de Erros Insuficiente ⚠️ **MÉDIO**

**Problema:**
- Erros são silenciados com `print()` genérico
- Não há logging estruturado
- Difícil debugar quando algo falha

**Solução:**
- Usar `StructuredLogger` para logs
- Adicionar mais informações de debug
- Melhorar mensagens de erro

---

## 🎯 Plano de Implementação

### Fase 1: Implementar Steam Community XML API (Método Principal)

**Arquivo:** `core/logs/steam_api.py`

**Mudanças:**
1. Implementar método `_get_steam_community_info()` usando **Steam Community XML API**
2. Usar parsing XML nativo do Python (sem dependências extras)
3. Extrair dados do XML retornado
4. Retornar dados no mesmo formato da Steam API oficial

**Vantagens da XML API:**
- ✅ Não requer dependências externas (BeautifulSoup, etc)
- ✅ Formato estruturado e estável
- ✅ Mais rápido que scraping HTML
- ✅ Dados mais confiáveis

**Código Proposto:**
```python
def _get_steam_community_info(self, steam_id: str) -> Dict[str, Any]:
    """
    Obter informações do jogador via Steam Community XML API (sem API key)
    
    Endpoint: http://steamcommunity.com/profiles/{steamid}/?xml=1
    
    Args:
        steam_id: Steam ID do jogador
        
    Returns:
        Dict com informações do jogador no mesmo formato da Steam API
    """
    try:
        import xml.etree.ElementTree as ET
        
        # URL da Steam Community XML API
        xml_url = f"http://steamcommunity.com/profiles/{steam_id}/?xml=1"
        
        print(f"OK: Consultando Steam Community XML API para {steam_id}")
        response = requests.get(xml_url, timeout=self.timeout)
        response.raise_for_status()
        
        # Parsear XML
        root = ET.fromstring(response.content)
        
        # Extrair dados do XML
        persona_name = root.findtext('steamID', 'Unknown Player')
        avatar_full = root.findtext('avatarFull', '')
        avatar_medium = root.findtext('avatarMedium', '')
        avatar_icon = root.findtext('avatarIcon', '')
        country_code = root.findtext('countryCode', '')
        profile_state = root.findtext('profileState', '0')
        profile_url = f"https://steamcommunity.com/profiles/{steam_id}"
        
        # Usar avatar full se disponível, senão medium, senão icon
        avatar_url = avatar_full or avatar_medium or avatar_icon
        
        # Converter profileState para int
        try:
            profile_state_int = int(profile_state)
        except (ValueError, TypeError):
            profile_state_int = 0
        
        player_info = {
            'steam_id': steam_id,
            'persona_name': persona_name,
            'avatar_url': avatar_icon,  # Avatar pequeno (padrão)
            'avatar_medium_url': avatar_medium,
            'avatar_full_url': avatar_full,
            'country_code': country_code,
            'profile_url': profile_url,
            'persona_state': profile_state_int,
            'community_visibility': 1 if profile_state_int > 0 else 0,
            'last_logoff': 0,
            'real_name': '',
            'time_created': 0
        }
        
        # Salvar no cache
        cache_key = f"player_{steam_id}"
        self.cache[cache_key] = (player_info, datetime.now().timestamp())
        
        print(f"OK: Dados obtidos do Steam Community XML para {steam_id}: {persona_name}")
        return player_info
        
    except ET.ParseError as e:
        print(f"ERRO: Erro ao parsear XML do Steam Community: {e}")
        return self._get_fallback_info(steam_id)
    except requests.exceptions.RequestException as e:
        print(f"ERRO: Erro de rede ao consultar Steam Community: {e}")
        return self._get_fallback_info(steam_id)
    except Exception as e:
        print(f"ERRO: Erro inesperado ao obter dados do Steam Community: {e}")
        return self._get_fallback_info(steam_id)
```

**Nota:** Usa apenas bibliotecas padrão do Python (`xml.etree.ElementTree`), sem dependências extras!

---

### Fase 2: Refatorar get_player_info() para Usar Steam Community XML como Principal

**Arquivo:** `core/logs/steam_api.py`

**Mudanças:**
1. Modificar método `get_player_info()` para:
   - **Sempre usar Steam Community XML API primeiro** (mais seguro)
   - Remover dependência de API key oficial
   - Manter API key como fallback opcional (se configurada)
   - Simplificar lógica

**Código Proposto:**
```python
def get_player_info(self, steam_id: str) -> Dict[str, Any]:
    """
    Obter informações básicas do jogador via Steam Community XML API
    
    Args:
        steam_id: Steam ID do jogador
        
    Returns:
        Dict com informações do jogador ou dados padrão se falhar
    """
    try:
        # Verificar cache primeiro
        cache_key = f"player_{steam_id}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now().timestamp() - timestamp < self.cache_timeout:
                print(f"OK: Dados do cache para {steam_id}")
                return cached_data
        
        # SEMPRE usar Steam Community XML API (não requer API key)
        print(f"OK: Consultando Steam Community XML API para {steam_id}")
        player_info = self._get_steam_community_info(steam_id)
        
        # Se obteve dados válidos (não é fallback), retornar
        if player_info.get('persona_name') != 'Unknown Player':
            return player_info
        
        # Se falhou, tentar API oficial como fallback (se configurada)
        if self.api_key:
            print(f"AVISO: Steam Community falhou, tentando API oficial para {steam_id}")
            return self._get_steam_api_info(steam_id)
        
        # Se tudo falhou, retornar fallback
        return self._get_fallback_info(steam_id)
                
    except Exception as e:
        print(f"ERRO: Erro ao obter dados do jogador: {e}")
        return self._get_fallback_info(steam_id)
```

**Nota:** Método `_get_steam_api_info()` seria o código atual que usa API oficial (mantido como fallback opcional).

---

### Fase 3: Melhorar Logging e Tratamento de Erros

**Arquivo:** `core/logs/steam_api.py`

**Mudanças:**
1. Adicionar `StructuredLogger` como dependência opcional
2. Substituir `print()` por logging adequado
3. Adicionar mais informações de debug
4. Adicionar tratamento de perfis privados

---

## 📦 Dependências

### ✅ Nenhuma Nova Dependência Necessária!

A solução usa apenas bibliotecas padrão do Python:
- `xml.etree.ElementTree` - Parsing XML (já incluído no Python)
- `requests` - Já está no `requirements.txt`

**Não é necessário adicionar:**
- ❌ `beautifulsoup4` - Não precisa mais
- ❌ `lxml` - Não precisa mais

---

## ✅ Checklist de Testes

- [ ] Testar com Steam ID válido e perfil público
- [ ] Testar com Steam ID válido e perfil privado
- [ ] Testar com Steam ID inválido
- [ ] Testar cache (múltiplas requisições do mesmo jogador)
- [ ] Testar timeout de cache (5 minutos)
- [ ] Verificar se avatar aparece no Discord
- [ ] Verificar se nome Steam aparece no Discord
- [ ] Verificar se link do perfil funciona
- [ ] Testar com perfil que não existe
- [ ] Verificar logs para debug
- [ ] Testar rate limiting (múltiplas requisições simultâneas)

---

## 🔄 Ordem de Execução

1. **Fase 1** - Implementar `_get_steam_community_info()` usando XML API (crítico)
2. **Fase 2** - Refatorar `get_player_info()` para usar XML API como principal (crítico)
3. **Fase 3** - Melhorar logging e tratamento de erros (opcional, pode ser feito depois)

---

## 📝 Notas Adicionais

### Vantagens da Steam Community XML API

**Segurança:**
- ✅ Não requer API key (elimina riscos de exposição)
- ✅ Não requer autenticação
- ✅ Não armazena credenciais

**Confiabilidade:**
- ✅ Endpoint oficial mantido pela Steam
- ✅ Formato XML estruturado e estável
- ✅ Menos propenso a quebrar que scraping HTML

**Performance:**
- ✅ Mais rápido que scraping HTML
- ✅ Dados já estruturados (não precisa parsear HTML complexo)
- ✅ Cache implementado (5 minutos)

**Limitações:**
- ⚠️ Perfis privados podem retornar dados limitados
- ⚠️ Pode ter rate limiting (mas menos restritivo que API oficial)
- ⚠️ Não retorna alguns dados avançados (como last_logoff preciso)

### Tratamento de Perfis Privados

Quando um perfil é privado:
- XML ainda retorna `steamID` (nome)
- Pode não retornar `avatarFull` (mas geralmente retorna `avatarIcon`)
- `profileState` pode ser 0
- Sistema deve funcionar mesmo com dados limitados

### Cache Strategy

- Cache de 5 minutos por jogador
- Reduz requisições desnecessárias
- Melhora performance em notificações de múltiplos jogadores

---

## 🚀 Próximos Passos

1. ✅ Revisar este planejamento
2. Implementar Fase 1 (`_get_steam_community_info()` com XML API)
3. Implementar Fase 2 (refatorar `get_player_info()`)
4. Testar em ambiente de desenvolvimento
5. Validar que nome e avatar aparecem no Discord
6. Deploy em produção

---

## 🔒 Considerações de Segurança

### Por que não usar API Key oficial?

1. **Risco de Exposição:**
   - API key precisa ser armazenada (mesmo criptografada)
   - Se comprometida, pode ser usada por terceiros
   - Pode esgotar quota da API

2. **Complexidade Desnecessária:**
   - Requer descriptografia
   - Requer gerenciamento de credenciais
   - Adiciona pontos de falha

3. **Steam Community XML API é Suficiente:**
   - Fornece todos os dados necessários (nome e avatar)
   - Não requer autenticação
   - É pública e estável

### Recomendação Final

**Usar Steam Community XML API como método principal** e remover dependência de API key oficial. Isso torna o sistema:
- ✅ Mais seguro
- ✅ Mais simples
- ✅ Mais fácil de manter
- ✅ Sem necessidade de gerenciar credenciais

