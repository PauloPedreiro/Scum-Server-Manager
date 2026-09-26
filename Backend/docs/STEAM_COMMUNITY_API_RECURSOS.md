# 🎮 Recursos da Steam Community API Pública

## 📋 Visão Geral

A Steam Community API oferece acesso a dados públicos da plataforma Steam **sem necessidade de API key**. Os dados são retornados em formato XML ou JSON através de endpoints públicos.

---

## 🔑 Características Principais

- ✅ **Pública**: Não requer autenticação ou API key
- ✅ **Gratuita**: Sem limites de quota (mas respeite rate limiting)
- ✅ **XML/JSON**: Dados estruturados e fáceis de parsear
- ✅ **Estável**: Endpoints mantidos oficialmente pela Valve

---

## 📚 Recursos Disponíveis

### 1. profile de Usuário (Perfil Individual)

#### Endpoint XML
```
http://steamcommunity.com/profiles/{steamid}/?xml=1
```

#### Campos Retornados (XML)
```xml
<profile>
    <steamID64>76561198000000000</steamID64>
    <steamID>NomeDoJogador</steamID>
    <onlineState>online/offline</onlineState>
    <stateMessage>Em jogo: Nome do Jogo</stateMessage>
    <privacyState>public/friends/private</privacyState>
    <visibilityState>1/3</visibilityState>
    <avatarIcon>URL do avatar pequeno</avatarIcon>
    <avatarMedium>URL do avatar médio</avatarMedium>
    <avatarFull>URL do avatar completo</avatarFull>
    <vacBanned>0/1</vacBanned>
    <tradeBanState>None/Limited</tradeBanState>
    <isLimitedAccount>0/1</isLimitedAccount>
    <customURL>custom-url-do-perfil</customURL>
    <memberSince>Data de criação da conta</memberSince>
    <location>País/Cidade</location>
    <realname>Nome Real (se público)</realname>
    <summary>Biografia do perfil</summary>
    <countryCode>BR</countryCode>
    <stateCode>Estado/Província</stateCode>
    <cityID>Código da cidade</cityID>
    <headline>Headline do perfil</headline>
    <groups>Lista de grupos</groups>
    <friends>Lista de amigos</friends>
</profile>
```

#### Exemplo de Uso
```python
import requests
import xml.etree.ElementTree as ET

steam_id = "76561198000000000"
url = f"http://steamcommunity.com/profiles/{steam_id}/?xml=1"
response = requests.get(url)
root = ET.fromstring(response.content)

nome = root.findtext('steamID')
avatar = root.findtext('avatarFull')
pais = root.findtext('countryCode')
```

---

### 2. 👥 Grupos da Comunidade

#### Endpoint XML - Lista de Membros
```
http://steamcommunity.com/groups/{group_name}/memberslistxml/?xml=1
```

#### Campos Retornados
```xml
<memberList>
    <groupID64>ID do grupo</groupID64>
    <groupDetails>
        <groupName>Nome do Grupo</groupName>
        <groupURL>URL do grupo</groupURL>
        <headline>Descrição do grupo</headline>
        <summary>Resumo do grupo</summary>
        <avatarIcon>URL do avatar</avatarIcon>
        <avatarMedium>URL do avatar médio</avatarMedium>
        <avatarFull>URL do avatar completo</avatarFull>
        <memberCount>Número de membros</memberCount>
        <membersInChat>Membros online no chat</membersInChat>
        <membersInGame>Membros em jogo</membersInGame>
        <membersOnline>Membros online</membersOnline>
    </groupDetails>
    <members>
        <steamID64>ID do membro</steamID64>
        <steamID>Nome do membro</steamID>
        <!-- ... mais membros ... -->
    </members>
</memberList>
```

#### Endpoint JSON - Informações do Grupo
```
http://steamcommunity.com/groups/{group_name}/memberslistjson/?json=1
```

---

### 3. 🎮 Inventário Público

#### Endpoint JSON
```
http://steamcommunity.com/inventory/{steamid}/{appid}/{contextid}/
```

**Parâmetros:**
- `steamid`: Steam ID do jogador
- `appid`: ID do jogo (ex: 730 para CS2, 570 para Dota 2)
- `contextid`: Contexto do inventário (geralmente 2)

#### Exemplo
```
http://steamcommunity.com/inventory/76561198000000000/730/2/
```

#### Campos Retornados (JSON)
```json
{
    "assets": [
        {
            "appid": 730,
            "contextid": "2",
            "assetid": "ID do item",
            "classid": "ID da classe",
            "instanceid": "ID da instância",
            "amount": "1"
        }
    ],
    "descriptions": [
        {
            "appid": 730,
            "classid": "ID da classe",
            "instanceid": "ID da instância",
            "name": "Nome do item",
            "type": "Tipo do item",
            "tradable": 1,
            "marketable": 1,
            "icon_url": "URL do ícone",
            "icon_url_large": "URL do ícone grande",
            "descriptions": [...],
            "tags": [...]
        }
    ],
    "total_inventory_count": 100,
    "success": 1
}
```

---

### 4. 🏆 Conquistas (Achievements)

#### Endpoint XML
```
http://steamcommunity.com/profiles/{steamid}/stats/{appid}/?xml=1
```

#### Exemplo
```
http://steamcommunity.com/profiles/76561198000000000/stats/730/?xml=1
```

#### Campos Retornados
```xml
<playerstats>
    <steamID64>ID do jogador</steamID64>
    <gameName>Nome do Jogo</gameName>
    <stats>
        <stat>
            <name>Nome da estatística</name>
            <value>Valor</value>
        </stat>
    </stats>
    <achievements>
        <achievement>
            <apiname>ID da conquista</apiname>
            <achieved>1/0</achieved>
            <unlocktime>Timestamp</unlocktime>
            <name>Nome da conquista</name>
            <description>Descrição</description>
        </achievement>
    </achievements>
</playerstats>
```

---

### 5. 🎯 Estatísticas de Jogos

#### Endpoint XML
```
http://steamcommunity.com/profiles/{steamid}/stats/{appid}/?xml=1
```

Retorna estatísticas detalhadas do jogador em um jogo específico.

---

### 6. 📊 Lista de Jogos (Owned Games)

#### Endpoint JSON (via Steam Web API - requer API key)
```
http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={API_KEY}&steamid={steamid}&format=json
```

**Nota:** Este endpoint requer API key, mas há alternativas públicas via scraping.

---

### 7. 👫 Lista de Amigos

#### Endpoint XML
```
http://steamcommunity.com/profiles/{steamid}/friends/?xml=1
```

#### Campos Retornados
```xml
<friendsList>
    <steamid>ID do jogador</steamid>
    <friends>
        <friend>
            <steamid64>ID do amigo</steamid64>
            <steamid>Nome do amigo</steamid>
            <relationship>friend</relationship>
            <friend_since>Timestamp</friend_since>
        </friend>
    </friends>
</friendsList>
```

---

### 8. 🏪 Steam Market (Mercado)

#### Endpoint JSON - Preços de Itens
```
http://steamcommunity.com/market/priceoverview/?country={country}&currency={currency}&appid={appid}&market_hash_name={item_name}
```

#### Parâmetros
- `country`: Código do país (ex: BR, US)
- `currency`: Código da moeda (ex: 1 para USD, 7 para BRL)
- `appid`: ID do jogo
- `market_hash_name`: Nome do item no mercado

#### Exemplo
```
http://steamcommunity.com/market/priceoverview/?country=BR&currency=7&appid=730&market_hash_name=AK-47%20%7C%20Redline%20%28Field-Tested%29
```

#### Campos Retornados
```json
{
    "success": true,
    "lowest_price": "R$ 15,00",
    "volume": "1.234",
    "median_price": "R$ 16,50"
}
```

---

### 9. 🎨 Workshop Items

#### Endpoint XML
```
http://steamcommunity.com/profiles/{steamid}/myworkshopfiles/?xml=1&appid={appid}
```

Retorna itens do Workshop criados pelo usuário.

---

### 10. 📝 Comentários de Perfil

#### Endpoint XML
```
http://steamcommunity.com/profiles/{steamid}/allcomments/?xml=1
```

Retorna comentários públicos do perfil.

---

## 🔍 Recursos Adicionais (Via Scraping HTML)

Alguns dados não estão disponíveis via XML/JSON, mas podem ser obtidos via scraping:

### Status em Jogo
- Jogo atual
- Tempo de jogo
- Status online/offline

### Badges e Nível Steam
- Nível da conta Steam
- Badges coletados
- XP total

### Atividade Recente
- Últimos jogos jogados
- Conquistas recentes
- Atividade na comunidade

---

## 📊 Comparação: Community API vs Web API

| Recurso | Community API (Pública) | Web API (Requer Key) |
|---------|------------------------|---------------------|
| Perfil de usuário | ✅ XML completo | ✅ JSON estruturado |
| Avatar | ✅ Sim | ✅ Sim |
| Lista de amigos | ✅ Sim | ✅ Sim |
| Inventário | ✅ Sim (público) | ✅ Sim (completo) |
| Conquistas | ✅ Sim (públicas) | ✅ Sim (completo) |
| Estatísticas | ✅ Sim (públicas) | ✅ Sim (completo) |
| Lista de jogos | ❌ Não | ✅ Sim |
| Tempo de jogo | ❌ Não | ✅ Sim |
| Grupos | ✅ Sim | ✅ Sim |
| Market prices | ✅ Sim | ❌ Não |

---

## ⚠️ Limitações e Considerações

### Perfis Privados
- Dados limitados ou não disponíveis
- `privacyState` indica o nível de privacidade
- Alguns campos podem estar vazios

### Rate Limiting
- Não há limite oficial documentado
- Recomenda-se respeitar delays entre requisições
- Evitar requisições muito frequentes

### Disponibilidade
- Endpoints podem estar temporariamente indisponíveis
- Steam pode mudar estrutura sem aviso prévio
- Sempre implementar tratamento de erros

### Dados Sensíveis
- Apenas dados públicos são acessíveis
- Informações privadas não estão disponíveis
- Respeite a privacidade dos usuários

---

## 🛠️ Exemplos de Implementação

### Python - Obter Perfil Completo
```python
import requests
import xml.etree.ElementTree as ET

def get_steam_profile(steam_id: str) -> dict:
    """Obter perfil completo do Steam via XML API"""
    url = f"http://steamcommunity.com/profiles/{steam_id}/?xml=1"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        return {
            'steam_id': root.findtext('steamID64'),
            'nome': root.findtext('steamID'),
            'avatar_full': root.findtext('avatarFull'),
            'avatar_medium': root.findtext('avatarMedium'),
            'avatar_icon': root.findtext('avatarIcon'),
            'pais': root.findtext('countryCode'),
            'estado_online': root.findtext('onlineState'),
            'privacidade': root.findtext('privacyState'),
            'banido_vac': root.findtext('vacBanned') == '1',
            'membro_desde': root.findtext('memberSince'),
            'localizacao': root.findtext('location'),
            'resumo': root.findtext('summary')
        }
    except Exception as e:
        print(f"Erro ao obter perfil: {e}")
        return {}
```

### Python - Obter Inventário
```python
def get_steam_inventory(steam_id: str, app_id: int = 730) -> dict:
    """Obter inventário público do Steam"""
    url = f"http://steamcommunity.com/inventory/{steam_id}/{app_id}/2/"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Erro ao obter inventário: {e}")
        return {}
```

### Python - Obter Preço no Market
```python
def get_market_price(item_name: str, app_id: int = 730, country: str = "BR", currency: int = 7) -> dict:
    """Obter preço de item no Steam Market"""
    import urllib.parse
    
    encoded_name = urllib.parse.quote(item_name)
    url = f"http://steamcommunity.com/market/priceoverview/?country={country}&currency={currency}&appid={app_id}&market_hash_name={encoded_name}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Erro ao obter preço: {e}")
        return {}
```

---

## 📚 Recursos Úteis

### Documentação Oficial
- Steam Web API: https://steampowered.com/steamcommunity/public/apis
- Steam Community: https://steamcommunity.com

### Bibliotecas Python
- `steamcom`: Biblioteca para Steam Community API
- `steam`: Wrapper para Steam Web API

### Ferramentas de Teste
- Postman Collections para Steam API
- Extensões de navegador para visualizar XML/JSON

---

## ✅ Resumo para Nosso Caso de Uso

Para o sistema de notificações de novos jogadores, precisamos apenas de:

1. **Perfil XML** (`/profiles/{steamid}/?xml=1`)
   - ✅ Nome do jogador (`steamID`)
   - ✅ Avatar completo (`avatarFull`)
   - ✅ País (`countryCode`)
   - ✅ Link do perfil

Isso é **suficiente** e **mais seguro** que usar API key oficial!

---

**Última atualização:** 2025-01-XX  
**Status:** ✅ Documentação completa dos recursos públicos disponíveis

