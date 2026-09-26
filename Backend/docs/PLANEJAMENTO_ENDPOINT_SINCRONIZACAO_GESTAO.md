# 📡 Planejamento: Endpoint de Sincronização com Gestão

> ✅ **STATUS: IMPLEMENTADO**  
> Data de implementação: 2025-12-XX  
> Arquivo: `core/communication/gestao_sync_service.py`  
> Integração: `main.py` (inicialização automática)

## 🎯 Objetivo

Criar um sistema onde o **SSM Backend** envia dados para o **Gestão** (de dentro para fora) para:
- Exibir rankings centralizados de todos os servidores
- Listar jogadores de todos os servidores
- Criar um banco de dados unificado no Gestão
- Identificar servidores de forma única usando hash

**Arquitetura:**
- SSM Backend faz requisições POST para o Gestão
- **NÃO precisa** abrir portas no SSM Backend (apenas no Gestão)
- Sistema de handshake: SSM pergunta se Gestão está pronto antes de enviar
- Se Gestão não estiver pronto, SSM aguarda e tenta novamente

**Identificação do Servidor:**
- O **hash** (`server_hash`) é o identificador único do servidor
- **Servidor DEVE estar cadastrado no Gestão ANTES de sincronizar**
- Gestão busca servidor pelo hash na tabela `Server`
- Se não encontrar → **REJEITA** (servidor não cadastrado)
- Se encontrar → valida API key e atualiza dados

**API Key:**
- **API key é gerada pelo Gestão** quando servidor é cadastrado
- Admin do Gestão cadastra servidor com hash
- Gestão gera API key única e retorna ao admin
- Admin configura API key no SSM Backend
- SSM Backend envia hash + api_key nas sincronizações

---

## 🔍 Análise da Proposta Original

### Proposta do Usuário:
```
/api/server/918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d
```

**Vantagens:**
- ✅ Hash como identificação única
- ✅ URL simples e direta

**Desvantagens:**
- ⚠️ Hash no path pode ser exposto em logs
- ⚠️ Se hash mudar, URL muda (pode quebrar links)
- ⚠️ Não há autenticação/autorização

---

## 💡 Solução Proposta: POST com Handshake

### **Arquitetura: SSM Backend envia para Gestão (de dentro para fora)**

O **SSM Backend** **envia** dados para o Gestão usando **POST** com sistema de handshake.

### **Fluxo com Handshake (Recomendado)** ⭐

```
1. SSM Backend → GET /api/servers/ready?server_hash={hash}
   ↓
   Gestão responde: { "ready": true } ou { "ready": false, "retry_after": 60 }
   ↓
2a. Se ready=true:
    SSM Backend → POST /api/servers/sync
    Body: { server_hash, server_info, players, rankings }
    ↓
    Gestão processa e responde: { "success": true }
   
2b. Se ready=false:
    SSM Backend aguarda "retry_after" segundos
    ↓
    Volta para passo 1 (tenta novamente)
```

### **Endpoints no Gestão**

#### **1. GET /api/servers/ready** (Health Check / Handshake)

Verifica se o Gestão está pronto para receber dados.

**Request:**
```
GET /api/servers/ready?server_hash={hash}
```

**Resposta (Pronto):**
```json
{
  "ready": true,
  "message": "Pronto para receber dados"
}
```

**Resposta (Não Pronto):**
```json
{
  "ready": false,
  "retry_after": 60,
  "message": "Servidor ocupado, tente novamente em 60 segundos"
}
```

**Resposta (Erro):**
```json
{
  "ready": false,
  "error": "Servidor hash não encontrado",
  "retry_after": 300
}
```

#### **2. POST /api/servers/sync** (Envio de Dados)

Recebe dados do SSM Backend.

**Request:**
```json
{
  "server_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d",
  "api_key": "server_api_key_here",
  "server_info": {
    "name": "Meu Servidor SCUM",
    "version": "3.0.0",
    "max_players": 64,
    "current_players": 32
  },
  "players": [...],
  "rankings": {...},
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Resposta (Sucesso):**
```json
{
  "success": true,
  "message": "Dados sincronizados com sucesso",
  "server_id": 1
}
```

**Resposta (Não Pronto - Deve tentar novamente):**
```json
{
  "success": false,
  "error": "Servidor ocupado",
  "retry_after": 30
}
```

### **Vantagens do Handshake**

✅ **Controle de carga**: Gestão pode recusar quando sobrecarregado
✅ **Rate limiting inteligente**: Gestão controla frequência de sincronização
✅ **Retry automático**: SSM Backend tenta novamente automaticamente
✅ **Não precisa abrir portas**: SSM Backend faz requisições outbound
✅ **Mais seguro**: Apenas Gestão expõe portas
✅ **Resiliente**: Se Gestão estiver offline, SSM aguarda e tenta depois

---

### **Opção 1: Hash no Header + Autenticação (RECOMENDADA)**

#### Endpoint:
```
POST /api/servers/sync
```

#### Headers:
```
X-Server-Hash: 918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d
X-Server-Key: <api_key_do_servidor>
Content-Type: application/json
```

#### Body:
```json
{
  "server_info": {
    "name": "Meu Servidor SCUM",
    "version": "3.0.0",
    "max_players": 64,
    "current_players": 32
  },
  "players": [
    {
      "steam_id": "76561198012345678",
      "name": "PlayerName",
      "fame": 15000,
      "is_online": true,
      "last_seen": "2025-01-15T10:30:00Z"
    }
  ],
  "rankings": {
    "survival": [...],
    "kills": [...],
    "lockpicking": [...],
    "fishing": [...]
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Vantagens:**
- ✅ Hash não exposto na URL
- ✅ Autenticação adicional com API key
- ✅ Mais seguro
- ✅ URL estável (não muda se hash mudar)

---

### **Opção 2: Hash no Path + Query Parameter (Alternativa)**

#### Endpoint:
```
POST /api/servers/{server_hash}/sync?api_key=<key>
```

**Vantagens:**
- ✅ Simples de implementar
- ✅ Hash visível na URL (pode ser útil para debug)

**Desvantagens:**
- ⚠️ Hash exposto em logs
- ⚠️ URL muda se hash mudar

---

### **Opção 3: Hash como Identificador Interno (Híbrida - MELHOR)**

#### Endpoint:
```
POST /api/servers/sync
```

#### Body:
```json
{
  "server_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d",
  "api_key": "server_api_key_here",
  "server_info": {...},
  "players": [...],
  "rankings": {...},
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Vantagens:**
- ✅ Hash no body (não exposto em logs de URL)
- ✅ API key para autenticação
- ✅ Flexível para mudanças futuras
- ✅ Fácil de validar no backend

---

## 🔄 Comparação: POST vs PUT vs PATCH

### **POST /api/servers/sync** (Recomendado)
```http
POST /api/servers/sync
Body: { server_hash, api_key, server_info, players, rankings }
```
**Quando usar:**
- ✅ Operação que pode criar OU atualizar (upsert)
- ✅ Payload grande (muitos dados)
- ✅ Não precisa de URL com ID específico
- ✅ Mais flexível para sincronização

### **PUT /api/server/{server_hash}** (Alternativa REST)
```http
PUT /api/server/918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d
Body: { api_key, server_info, players, rankings }
```
**Quando usar:**
- ✅ Operação idempotente (mesmo request = mesmo resultado)
- ✅ URL identifica o recurso
- ✅ Substitui o recurso completo
- ⚠️ Hash fica na URL (exposto em logs)

### **PATCH /api/server/{server_hash}** (Atualização parcial)
```http
PATCH /api/server/918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d
Body: { players: [...], rankings: {...} }
```
**Quando usar:**
- ✅ Atualizar apenas campos específicos
- ✅ Não substituir tudo
- ⚠️ Menos comum para sincronização completa

**Decisão:** Usamos **POST** porque é mais flexível e adequado para sincronização que pode criar ou atualizar.

---

### **Opção 4: PUT com Hash no Path (Alternativa REST)**

Se preferir seguir padrão REST mais estrito:

#### Endpoint:
```
PUT /api/server/{server_hash}
```

#### Body:
```json
{
  "api_key": "server_api_key_here",
  "server_info": {...},
  "players": [...],
  "rankings": {...},
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Vantagens:**
- ✅ Segue padrão REST (PUT para criar/atualizar recurso identificado na URL)
- ✅ URL identifica claramente o recurso
- ✅ Idempotente (mesmo request = mesmo resultado)

**Desvantagens:**
- ⚠️ Hash exposto na URL (aparece em logs)
- ⚠️ Se hash mudar, URL muda (pode quebrar links)

**Recomendação:** Se não se importar com hash na URL, PUT é uma boa opção REST.

---

## 🏗️ Arquitetura Proposta

### **1. No Gestão (Backend Flask)**

#### Modelo de Dados:
```python
# Gestão/app/models/server.py

class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    server_name = db.Column(db.String(255))
    version = db.Column(db.String(50))
    max_players = db.Column(db.Integer)
    current_players = db.Column(db.Integer)
    api_key = db.Column(db.String(255), unique=True)  # Para autenticação
    is_active = db.Column(db.Boolean, default=True)
    last_sync = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ServerPlayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    steam_id = db.Column(db.String(20), nullable=False, index=True)
    player_name = db.Column(db.String(255))
    fame = db.Column(db.Integer, default=0)
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('server_id', 'steam_id', name='uq_server_player'),
    )

class ServerRanking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    ranking_type = db.Column(db.String(50))  # survival, kills, lockpicking, etc
    steam_id = db.Column(db.String(20), nullable=False, index=True)
    player_name = db.Column(db.String(255))
    rank = db.Column(db.Integer)
    score = db.Column(db.Float)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_server_ranking_type', 'server_id', 'ranking_type'),
    )
```

#### Endpoint:
```python
# Gestão/app/routes/servers.py

@bp.route('/api/servers/sync', methods=['POST'])
def sync_server_data():
    """
    Recebe dados de sincronização de um servidor SSM
    
    Body:
    {
        "server_hash": "hash_do_servidor",
        "api_key": "chave_api",
        "server_info": {...},
        "players": [...],
        "rankings": {...},
        "timestamp": "ISO8601"
    }
    """
    data = request.get_json()
    
    # 1. Validar dados obrigatórios
    server_hash = data.get('server_hash')
    api_key = data.get('api_key')
    
    if not server_hash or not api_key:
        return jsonify({
            'success': False,
            'error': 'server_hash e api_key são obrigatórios'
        }), 400
    
    # 2. Autenticar servidor
    server = Server.query.filter_by(server_hash=server_hash).first()
    
    if not server:
        # Primeira sincronização - criar servidor
        server = Server(
            server_hash=server_hash,
            api_key=api_key,
            server_name=data.get('server_info', {}).get('name', 'Servidor Desconhecido'),
            version=data.get('server_info', {}).get('version'),
            max_players=data.get('server_info', {}).get('max_players'),
            current_players=data.get('server_info', {}).get('current_players')
        )
        db.session.add(server)
        db.session.flush()  # Para obter o ID
    else:
        # Verificar API key
        if server.api_key != api_key:
            return jsonify({
                'success': False,
                'error': 'API key inválida'
            }), 401
        
        # Atualizar informações do servidor
        server_info = data.get('server_info', {})
        server.server_name = server_info.get('name', server.server_name)
        server.current_players = server_info.get('current_players', 0)
        server.last_sync = datetime.utcnow()
    
    # 3. Sincronizar jogadores
    players_data = data.get('players', [])
    for player_data in players_data:
        player = ServerPlayer.query.filter_by(
            server_id=server.id,
            steam_id=player_data['steam_id']
        ).first()
        
        if player:
            # Atualizar
            player.player_name = player_data.get('name', player.player_name)
            player.fame = player_data.get('fame', 0)
            player.is_online = player_data.get('is_online', False)
            player.last_seen = parse_iso_datetime(player_data.get('last_seen'))
            player.synced_at = datetime.utcnow()
        else:
            # Criar novo
            player = ServerPlayer(
                server_id=server.id,
                steam_id=player_data['steam_id'],
                player_name=player_data.get('name'),
                fame=player_data.get('fame', 0),
                is_online=player_data.get('is_online', False),
                last_seen=parse_iso_datetime(player_data.get('last_seen'))
            )
            db.session.add(player)
    
    # 4. Sincronizar rankings
    rankings_data = data.get('rankings', {})
    for ranking_type, rankings in rankings_data.items():
        # Limpar rankings antigos deste tipo
        ServerRanking.query.filter_by(
            server_id=server.id,
            ranking_type=ranking_type
        ).delete()
        
        # Inserir novos rankings
        for rank, ranking_data in enumerate(rankings, start=1):
            ranking = ServerRanking(
                server_id=server.id,
                ranking_type=ranking_type,
                steam_id=ranking_data['steam_id'],
                player_name=ranking_data.get('name'),
                rank=rank,
                score=ranking_data.get('score', 0)
            )
            db.session.add(ranking)
    
    # 5. Commit
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Dados sincronizados com sucesso',
            'server_id': server.id
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Erro ao sincronizar: {str(e)}'
        }), 500
```

---

### **2. No Gestão - Endpoint de Handshake**

#### **GET /api/servers/ready** (Health Check)

```python
# Gestão/app/routes/servers.py

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from app.models.server import Server
import threading

bp = Blueprint('servers', __name__, url_prefix='/api')

# Controle de carga (pode ser melhorado com Redis em produção)
_sync_lock = threading.Lock()
_last_sync_times = {}  # {server_hash: datetime}
_max_concurrent_syncs = 5  # Máximo de sincronizações simultâneas
_current_syncs = 0

@bp.route('/servers/ready', methods=['GET'])
def check_ready():
    """
    Verifica se o Gestão está pronto para receber dados
    
    GET /api/servers/ready?server_hash={hash}
    """
    server_hash = request.args.get('server_hash')
    
    if not server_hash:
        return jsonify({
            'ready': False,
            'error': 'server_hash é obrigatório',
            'retry_after': 60
        }), 400
    
    # Validar formato do hash
    if len(server_hash) != 64 or not all(c in '0123456789abcdef' for c in server_hash.lower()):
        return jsonify({
            'ready': False,
            'error': 'Formato de hash inválido',
            'retry_after': 60
        }), 400
    
    with _sync_lock:
        # Verificar se já está sincronizando muitos servidores
        if _current_syncs >= _max_concurrent_syncs:
            return jsonify({
                'ready': False,
                'retry_after': 30,
                'message': 'Servidor ocupado, tente novamente em 30 segundos'
            }), 503
        
        # Verificar se este servidor sincronizou recentemente (rate limiting)
        if server_hash in _last_sync_times:
            last_sync = _last_sync_times[server_hash]
            min_interval = timedelta(seconds=60)  # Mínimo 1 minuto entre syncs
            
            if datetime.utcnow() - last_sync < min_interval:
                remaining = (min_interval - (datetime.utcnow() - last_sync)).seconds
                return jsonify({
                    'ready': False,
                    'retry_after': remaining,
                    'message': f'Sincronização muito recente, aguarde {remaining} segundos'
                }), 429
        
        # Verificar se servidor existe e está cadastrado
        server = Server.query.filter_by(server_hash=server_hash).first()
        if not server:
            # Servidor não cadastrado - REJEITAR
            return jsonify({
                'ready': False,
                'error': 'Servidor não cadastrado no Gestão',
                'retry_after': 300  # Aguardar 5 minutos antes de tentar novamente
            }), 403
        
        # Verificar se servidor está ativo
        if not server.is_active:
            return jsonify({
                'ready': False,
                'error': 'Servidor desativado',
                'retry_after': 300
            }), 403
        
        # Tudo OK - pronto para receber
        return jsonify({
            'ready': True,
            'message': 'Pronto para receber dados'
        }), 200
```

#### **POST /api/servers/sync** (Receber Dados)

```python
@bp.route('/servers/sync', methods=['POST'])
def sync_server_data():
    """
    Recebe dados de sincronização de um servidor SSM
    
    Body:
    {
        "server_hash": "hash_do_servidor",
        "api_key": "chave_api",
        "server_info": {...},
        "players": [...],
        "rankings": {...},
        "timestamp": "ISO8601"
    }
    """
    global _current_syncs, _last_sync_times
    
    data = request.get_json()
    
    # 1. Validar dados obrigatórios
    server_hash = data.get('server_hash')
    api_key = data.get('api_key')
    
    if not server_hash or not api_key:
        return jsonify({
            'success': False,
            'error': 'server_hash e api_key são obrigatórios'
        }), 400
    
        # 2. Verificar se está pronto (double-check)
        with _sync_lock:
            if _current_syncs >= _max_concurrent_syncs:
                return jsonify({
                    'success': False,
                    'error': 'Servidor ocupado',
                    'retry_after': 30
                }), 503
            
            _current_syncs += 1
    
    try:
        # 3. Identificar servidor pelo HASH
        # Servidor DEVE estar cadastrado ANTES de sincronizar
        server = Server.query.filter_by(server_hash=server_hash).first()
        
        if not server:
            # Servidor NÃO cadastrado - REJEITAR
            return jsonify({
                'success': False,
                'error': 'Servidor não cadastrado no Gestão. Cadastre o servidor antes de sincronizar.',
                'retry_after': 300
            }), 403
        
        # Verificar se servidor está ativo
        if not server.is_active:
            return jsonify({
                'success': False,
                'error': 'Servidor desativado no Gestão',
                'retry_after': 300
            }), 403
        
        # 4. Validar API key (deve ser igual ao cadastrado no Gestão)
        if server.api_key != api_key:
            return jsonify({
                'success': False,
                'error': 'API key inválida. Verifique a API key configurada no SSM Backend.',
                'retry_after': 0  # Não tentar novamente - erro de configuração
            }), 401
        
        # 5. Atualizar informações do servidor
        server_info = data.get('server_info', {})
        server.server_name = server_info.get('name', server.server_name)
        server.current_players = server_info.get('current_players', 0)
        server.last_sync = datetime.utcnow()
        # Log para debug
        print(f"✅ Servidor sincronizado: {server.server_name} (hash: {server_hash[:16]}...)")
        
        # 4. Sincronizar jogadores
        players_data = data.get('players', [])
        for player_data in players_data:
            player = ServerPlayer.query.filter_by(
                server_id=server.id,
                steam_id=player_data['steam_id']
            ).first()
            
            if player:
                player.player_name = player_data.get('name', player.player_name)
                player.fame = player_data.get('fame', 0)
                player.is_online = player_data.get('is_online', False)
                player.last_seen = parse_iso_datetime(player_data.get('last_seen'))
                player.synced_at = datetime.utcnow()
            else:
                player = ServerPlayer(
                    server_id=server.id,
                    steam_id=player_data['steam_id'],
                    player_name=player_data.get('name'),
                    fame=player_data.get('fame', 0),
                    is_online=player_data.get('is_online', False),
                    last_seen=parse_iso_datetime(player_data.get('last_seen'))
                )
                db.session.add(player)
        
        # 5. Sincronizar rankings
        rankings_data = data.get('rankings', {})
        for ranking_type, rankings in rankings_data.items():
            ServerRanking.query.filter_by(
                server_id=server.id,
                ranking_type=ranking_type
            ).delete()
            
            for rank, ranking_data in enumerate(rankings, start=1):
                ranking = ServerRanking(
                    server_id=server.id,
                    ranking_type=ranking_type,
                    steam_id=ranking_data['steam_id'],
                    player_name=ranking_data.get('name'),
                    rank=rank,
                    score=ranking_data.get('score', 0)
                )
                db.session.add(ranking)
        
        # 6. Commit
        db.session.commit()
        
        # 7. Atualizar controle de carga
        with _sync_lock:
            _current_syncs -= 1
            _last_sync_times[server_hash] = datetime.utcnow()
        
        return jsonify({
            'success': True,
            'message': 'Dados sincronizados com sucesso',
            'server_id': server.id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        
        with _sync_lock:
            _current_syncs -= 1
        
        return jsonify({
            'success': False,
            'error': f'Erro ao sincronizar: {str(e)}'
        }), 500
```

---

### **3. No SSM Backend**

#### Serviço de Sincronização com Handshake:
```python
# Backend/core/communication/gestao_sync_service.py

class GestaoSyncService:
    """
    Serviço para sincronizar dados com o servidor de Gestão
    """
    
    def __init__(self, config: Dict[str, Any], logger):
        self.config = config
        self.logger = logger
        self.gestao_url = config.get('gestao_url')  # URL do Gestão
        self.sync_interval = config.get('sync_interval', 14400)  # 4 horas (14400 segundos)
        self.api_key = config.get('api_key')  # API key do servidor
        
        # Obter hardware fingerprint
        from core.licensing.hardware_fingerprint import HardwareFingerprint
        self.hardware_fingerprint = HardwareFingerprint()
        
    def get_server_hash(self) -> str:
        """Obter hash do servidor (equipment_hash)"""
        hash_value, _ = self.hardware_fingerprint.generate()
        return hash_value
    
    def check_ready(self) -> Tuple[bool, int]:
        """
        Verificar se o Gestão está pronto para receber dados (Handshake)
        
        Returns:
            (ready: bool, retry_after: int) - Se pronto e tempo para retry
        """
        try:
            server_hash = self.get_server_hash()
            
            response = requests.get(
                f"{self.gestao_url}/api/servers/ready",
                params={"server_hash": server_hash},
                timeout=self.config.get('handshake_timeout', 5)
            )
            
            if response.status_code == 200:
                data = response.json()
                return (data.get('ready', False), 0)
            elif response.status_code == 503:  # Servidor ocupado
                data = response.json()
                retry_after = data.get('retry_after', 30)
                self.logger.info(f"Gestão ocupado, aguardar {retry_after} segundos")
                return (False, retry_after)
            elif response.status_code == 429:  # Rate limit
                data = response.json()
                retry_after = data.get('retry_after', 60)
                self.logger.info(f"Rate limit atingido, aguardar {retry_after} segundos")
                return (False, retry_after)
            else:
                self.logger.warning(f"Resposta inesperada do handshake: {response.status_code}")
                return (False, 60)  # Aguardar 1 minuto
                
        except requests.exceptions.Timeout:
            self.logger.warning("Timeout ao verificar se Gestão está pronto")
            return (False, 30)
        except requests.exceptions.ConnectionError:
            self.logger.warning("Gestão offline, aguardar antes de tentar novamente")
            return (False, 300)  # Aguardar 5 minutos se offline
        except Exception as e:
            self.logger.error(f"Erro ao verificar se Gestão está pronto: {e}")
            return (False, 60)
    
    def sync_data(self) -> Dict[str, Any]:
        """
        Sincronizar dados com o Gestão (com handshake)
        """
        try:
            # 1. Handshake - verificar se Gestão está pronto
            ready, retry_after = self.check_ready()
            
            if not ready:
                return {
                    "success": False,
                    "error": "Gestão não está pronto",
                    "retry_after": retry_after,
                    "should_retry": True
                }
            
            # 2. Coletar dados
            server_hash = self.get_server_hash()
            server_info = self._get_server_info()
            players = self._get_players_data()
            rankings = self._get_rankings_data()
            
            # 3. Preparar payload
            payload = {
                "server_hash": server_hash,
                "api_key": self.api_key,
                "server_info": server_info,
                "players": players,
                "rankings": rankings,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 4. Enviar para Gestão
            response = requests.post(
                f"{self.gestao_url}/api/servers/sync",
                json=payload,
                timeout=self.config.get('sync_timeout', 30),
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                self.logger.info("Dados sincronizados com sucesso com Gestão")
                return {"success": True, "data": response.json()}
            elif response.status_code == 503:  # Servidor ocupado
                data = response.json()
                retry_after = data.get('retry_after', 30)
                self.logger.warning(f"Gestão ocupado durante sync, aguardar {retry_after} segundos")
                return {
                    "success": False,
                    "error": "Servidor ocupado",
                    "retry_after": retry_after,
                    "should_retry": True
                }
            else:
                self.logger.error(f"Erro ao sincronizar: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": response.text,
                    "should_retry": False
                }
                
        except requests.exceptions.Timeout:
            self.logger.error("Timeout ao sincronizar com Gestão")
            return {
                "success": False,
                "error": "Timeout",
                "retry_after": 60,
                "should_retry": True
            }
        except requests.exceptions.ConnectionError:
            self.logger.error("Gestão offline")
            return {
                "success": False,
                "error": "Gestão offline",
                "retry_after": 300,
                "should_retry": True
            }
        except Exception as e:
            self.logger.error(f"Erro ao sincronizar com Gestão: {e}")
            return {
                "success": False,
                "error": str(e),
                "should_retry": False
            }
    
    def sync_with_retry(self, max_retries: int = 3) -> Dict[str, Any]:
        """
        Sincronizar com retry automático
        
        Args:
            max_retries: Número máximo de tentativas
        
        Returns:
            Resultado da sincronização
        """
        for attempt in range(max_retries):
            result = self.sync_data()
            
            if result.get("success"):
                return result
            
            # Verificar se deve tentar novamente
            if not result.get("should_retry", False):
                return result
            
            # Aguardar antes de tentar novamente
            retry_after = result.get("retry_after", 60)
            max_delay = self.config.get('max_retry_delay', 3600)
            retry_after = min(retry_after, max_delay)
            
            if attempt < max_retries - 1:
                self.logger.info(f"Aguardando {retry_after} segundos antes de tentar novamente...")
                time.sleep(retry_after)
        
        return result
    
    def start_periodic_sync(self):
        """
        Iniciar sincronização periódica com handshake
        
        Executa em thread separada, fazendo:
        1. Verifica se Gestão está pronto (handshake)
        2. Se pronto, envia dados
        3. Se não pronto, aguarda e tenta novamente
        4. Repete a cada sync_interval segundos
        """
        import threading
        import time
        
        def sync_loop():
            while True:
                try:
                    self.logger.info("Iniciando tentativa de sincronização com Gestão...")
                    
                    # Tentar sincronizar (com retry automático)
                    result = self.sync_with_retry(max_retries=3)
                    
                    if result.get("success"):
                        self.logger.info("✅ Sincronização concluída com sucesso")
                    else:
                        error = result.get("error", "Erro desconhecido")
                        retry_after = result.get("retry_after", self.sync_interval)
                        self.logger.warning(f"❌ Sincronização falhou: {error}. Próxima tentativa em {retry_after}s")
                    
                    # Aguardar antes da próxima tentativa
                    wait_time = result.get("retry_after", self.sync_interval)
                    wait_time = min(wait_time, self.sync_interval)  # Não esperar mais que o intervalo normal
                    time.sleep(wait_time)
                    
                except Exception as e:
                    self.logger.error(f"Erro no loop de sincronização: {e}")
                    time.sleep(self.sync_interval)
        
        # Iniciar thread
        sync_thread = threading.Thread(target=sync_loop, daemon=True)
        sync_thread.start()
        self.logger.info(f"Sincronização periódica iniciada (intervalo: {self.sync_interval}s)")
        return sync_thread
```
    
    def _get_server_info(self) -> Dict[str, Any]:
        """Obter informações do servidor"""
        # Usar dados do config e server_manager
        return {
            "name": self.config.get('communication', {}).get('server_name', 'Servidor SCUM'),
            "version": "3.0.0",  # Versão do SSM
            "max_players": self.config.get('server', {}).get('max_players', 64),
            "current_players": self._get_current_players_count()
        }
    
    def _get_players_data(self) -> List[Dict[str, Any]]:
        """Obter dados dos jogadores"""
        # Consultar banco de dados SSM
        # Retornar lista de jogadores com steam_id, nome, fama, etc.
        pass
    
    def _get_rankings_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Obter dados de rankings - REUTILIZA lógica dos endpoints existentes
        
        Reutiliza a mesma lógica que:
        - GET /api/rankings?category=kills
        - GET /api/rankings?category=survival
        - GET /api/rankings/list
        """
        import sqlite3
        from utils.config_path_helper import ConfigPathHelper
        
        rankings_data = {}
        db_path = ConfigPathHelper().get_ssm_database_path()
        
        if not os.path.exists(db_path):
            self.logger.error(f"Banco SSM.db não encontrado: {db_path}")
            return rankings_data
        
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 1. Ranking de Kills (Top Killers)
            cursor.execute('''
                SELECT steam_id, player_name, kills, deaths, kdr
                FROM rankings
                WHERE kills > 0
                ORDER BY kills DESC, kdr DESC
                LIMIT 100
            ''')
            rankings_data['kills'] = [
                {
                    'steam_id': row['steam_id'],
                    'name': row['player_name'],
                    'score': row['kills'],
                    'kdr': row['kdr'],
                    'deaths': row['deaths']
                }
                for row in cursor.fetchall()
            ]
            
            # 2. Ranking de Survival (Minutos Sobrevividos)
            cursor.execute('''
                SELECT steam_id, player_name, minutes_survived, total_fame
                FROM rankings
                WHERE minutes_survived > 0
                ORDER BY minutes_survived DESC
                LIMIT 100
            ''')
            rankings_data['survival'] = [
                {
                    'steam_id': row['steam_id'],
                    'name': row['player_name'],
                    'score': row['minutes_survived'],
                    'fame': row['total_fame']
                }
                for row in cursor.fetchall()
            ]
            
            # 3. Ranking de Lockpicking (Taxa de Sucesso Geral)
            cursor.execute('''
                SELECT steam_id, player_name,
                       (lockpick_basic_rate + lockpick_medium_rate + 
                        lockpick_advanced_rate + lockpick_veryeasy_rate + 
                        lockpick_diallock_rate) / 5.0 as avg_rate,
                       lockpick_basic_rate, lockpick_medium_rate, 
                       lockpick_advanced_rate
                FROM rankings
                WHERE (lockpick_basic_rate + lockpick_medium_rate + 
                       lockpick_advanced_rate + lockpick_veryeasy_rate + 
                       lockpick_diallock_rate) > 0
                ORDER BY avg_rate DESC
                LIMIT 100
            ''')
            rankings_data['lockpicking'] = [
                {
                    'steam_id': row['steam_id'],
                    'name': row['player_name'],
                    'score': round(row['avg_rate'], 2),
                    'basic_rate': row['lockpick_basic_rate'],
                    'medium_rate': row['lockpick_medium_rate'],
                    'advanced_rate': row['lockpick_advanced_rate']
                }
                for row in cursor.fetchall()
            ]
            
            # 4. Ranking de Fishing (se houver dados)
            # Nota: Verificar se existe tabela de fishing ou usar dados de rankings
            try:
                cursor.execute('''
                    SELECT steam_id, player_name, animals_killed as fishing_score
                    FROM rankings
                    WHERE animals_killed > 0
                    ORDER BY animals_killed DESC
                    LIMIT 100
                ''')
                rankings_data['fishing'] = [
                    {
                        'steam_id': row['steam_id'],
                        'name': row['player_name'],
                        'score': row['fishing_score']
                    }
                    for row in cursor.fetchall()
                ]
            except Exception as e:
                self.logger.warning(f"Erro ao buscar ranking de fishing: {e}")
                rankings_data['fishing'] = []
        
        return rankings_data
    
    def _get_players_data(self) -> List[Dict[str, Any]]:
        """
        Obter dados dos jogadores - REUTILIZA lógica dos endpoints existentes
        
        Reutiliza a mesma lógica que:
        - GET /api/players/online
        - GET /api/players/online/list
        """
        import sqlite3
        from utils.config_path_helper import ConfigPathHelper
        from datetime import datetime
        
        players_data = []
        db_path = ConfigPathHelper().get_ssm_database_path()
        
        if not os.path.exists(db_path):
            self.logger.error(f"Banco SSM.db não encontrado: {db_path}")
            return players_data
        
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Buscar todos os jogadores (online e offline)
            # Usar tabela players_online para status e última atividade
            cursor.execute('''
                SELECT 
                    po.steam_id,
                    COALESCE(po.player_name, r.player_name, 'Unknown') as player_name,
                    COALESCE(r.total_fame, 0) as fame,
                    CASE WHEN po.status = 'online' THEN 1 ELSE 0 END as is_online,
                    po.last_activity as last_seen
                FROM players_online po
                LEFT JOIN rankings r ON po.steam_id = r.steam_id
                UNION
                SELECT 
                    r.steam_id,
                    r.player_name,
                    COALESCE(r.total_fame, 0) as fame,
                    0 as is_online,
                    NULL as last_seen
                FROM rankings r
                WHERE r.steam_id NOT IN (SELECT steam_id FROM players_online)
                ORDER BY fame DESC
                LIMIT 1000
            ''')
            
            for row in cursor.fetchall():
                players_data.append({
                    'steam_id': row['steam_id'],
                    'name': row['player_name'],
                    'fame': row['fame'],
                    'is_online': bool(row['is_online']),
                    'last_seen': row['last_seen'].isoformat() if row['last_seen'] else None
                })
        
        return players_data
    
    def _get_current_players_count(self) -> int:
        """Obter número de jogadores online"""
        import sqlite3
        from utils.config_path_helper import ConfigPathHelper
        
        db_path = ConfigPathHelper().get_ssm_database_path()
        if not os.path.exists(db_path):
            return 0
        
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM players_online WHERE status = 'online'")
                return cursor.fetchone()[0]
        except Exception as e:
            self.logger.error(f"Erro ao contar jogadores online: {e}")
            return 0
```

---

## 🔄 Fluxo de Funcionamento com Handshake

### **Fluxo Completo (com Handshake)**

```
┌─────────────────┐                                    ┌──────────────┐
│  SSM Backend     │                                    │   Gestão      │
│                 │                                    │               │
│ 1. Timer        │                                    │               │
│    dispara      │                                    │               │
│    (5 min)      │                                    │               │
│                 │                                    │               │
│ 2. Handshake    │ ──── GET /api/servers/ready ────> │               │
│                 │    ?server_hash={hash}            │               │
│                 │                                    │               │
│                 │ <──── {ready: true} ───────────── │               │
│                 │                                    │               │
│ 3. Se ready:    │                                    │               │
│    Coletar      │                                    │               │
│    dados        │                                    │               │
│                 │                                    │               │
│ 4. Enviar       │ ──── POST /api/servers/sync ────> │               │
│    dados        │    {server_hash, players, ...}    │               │
│                 │                                    │               │
│                 │ <──── {success: true} ──────────── │               │
│                 │                                    │               │
│ 5. Aguardar     │                                    │               │
│    próximo      │                                    │               │
│    ciclo        │                                    │               │
└─────────────────┘                                    └──────────────┘
```

### **1. Handshake (Verificação de Prontidão)**

```
SSM Backend → GET /api/servers/ready?server_hash={hash}
  ↓
Gestão verifica:
  - Está sobrecarregado? (muitas syncs simultâneas)
  - Rate limit? (sync muito recente deste servidor)
  - Servidor existe? (primeira vez)
  ↓
Resposta:
  - {ready: true} → Pode enviar
  - {ready: false, retry_after: 60} → Aguardar 60s
```

### **2. Envio de Dados (se ready=true)**

```
SSM Backend → POST /api/servers/sync
  ↓
Body: {
  server_hash: "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d",
  api_key: "abc123xyz789",  // API key gerada pelo Gestão
  server_info: {
    name: "Meu Servidor SCUM",
    ...
  },
  players: [...],
  rankings: {...}
}
  ↓
Gestão:
  1. Busca Server WHERE server_hash = "918aabd..."
  2. Se NÃO encontrar:
     → REJEITA (403 Forbidden)
     → Erro: "Servidor não cadastrado no Gestão"
     → SSM deve aguardar e tentar depois
  3. Se encontrar:
     → Verifica se is_active = true
     → Valida api_key (deve ser igual ao cadastrado)
     → Se api_key inválida → REJEITA (401 Unauthorized)
     → Se válida → Atualiza informações
  4. Sincroniza jogadores e rankings
  5. Retorna {success: true, server_id: 1}
```

**⚠️ IMPORTANTE: Servidor DEVE estar cadastrado ANTES!**

O Gestão identifica o servidor pelo **`server_hash`** enviado no body do POST:

1. **Servidor DEVE estar cadastrado no Gestão:**
   - Admin cadastra servidor manualmente no Gestão
   - Admin informa o `server_hash` do SSM Backend
   - Gestão gera `api_key` única e retorna ao admin
   - Admin configura `api_key` no SSM Backend

2. **Sincronização:**
   - SSM Backend envia POST com `server_hash` + `api_key`
   - Gestão busca `Server WHERE server_hash = {hash}`
   - Se não encontrar → **REJEITA** (servidor não cadastrado)
   - Se encontrar → valida `api_key` → sincroniza dados

**Fluxo de Cadastro:**
```
1. Admin obtém hash do SSM Backend
2. Admin acessa Gestão → Cadastra Servidor
3. Gestão gera API key única
4. Admin copia API key
5. Admin configura API key no SSM Backend (config.json)
6. SSM Backend pode sincronizar
```

### **3. Se Gestão Não Estiver Pronto**

```
SSM Backend → GET /api/servers/ready
  ↓
Gestão responde: {ready: false, retry_after: 30}
  ↓
SSM Backend:
  - Aguarda 30 segundos
  - Tenta handshake novamente
  - Repete até Gestão estar pronto
```

### **4. Se Gestão Estiver Offline**

```
SSM Backend → GET /api/servers/ready
  ↓
Erro de conexão (timeout/connection error)
  ↓
SSM Backend:
  - Aguarda 5 minutos (300s)
  - Tenta handshake novamente
  - Continua tentando até Gestão voltar
```

### **5. Retry Automático**

```
SSM Backend tenta sincronizar:
  ↓
Tentativa 1: Handshake → ready=false, retry_after=30
  ↓ (aguarda 30s)
Tentativa 2: Handshake → ready=true → Envia dados
  ↓
Se POST falhar com 503 (ocupado):
  - Aguarda retry_after segundos
  - Tenta novamente (até 3 tentativas)
```

### **Vantagens do Handshake**

✅ **Controle de carga**: Gestão pode recusar quando sobrecarregado
✅ **Rate limiting**: Evita sincronizações muito frequentes
✅ **Resiliente**: SSM aguarda automaticamente se Gestão não estiver pronto
✅ **Eficiente**: Não envia dados grandes se Gestão não pode processar
✅ **Retry inteligente**: Aguarda tempo apropriado antes de tentar novamente

---

## 🔒 Segurança

### **1. Autenticação**
- ✅ API key obrigatória
- ✅ Validação de server_hash + api_key
- ✅ Rate limiting (máximo X requisições por minuto)

### **2. Validação de Dados**
- ✅ Validar formato do hash (64 caracteres hex)
- ✅ Validar timestamp (não muito antigo)
- ✅ Validar estrutura dos dados

### **3. Proteção contra Ataques**
- ✅ CORS configurado
- ✅ Validação de tamanho do payload
- ✅ Timeout nas requisições
- ✅ Logs de tentativas de acesso

---

## 📊 Estrutura de Dados

### **Server Info:**
```json
{
  "name": "Meu Servidor SCUM",
  "version": "3.0.0",
  "max_players": 64,
  "current_players": 32
}
```

### **Players:**
```json
[
  {
    "steam_id": "76561198012345678",
    "name": "PlayerName",
    "fame": 15000,
    "is_online": true,
    "last_seen": "2025-01-15T10:30:00Z"
  }
]
```

### **Rankings:**
```json
{
  "survival": [
    {
      "steam_id": "76561198012345678",
      "name": "PlayerName",
      "score": 95.5,
      "rank": 1
    }
  ],
  "kills": [...],
  "lockpicking": [...],
  "fishing": [...]
}
```

---

## 🔍 Endpoints de Consulta (GET)

### **Endpoint Principal: Consultar Servidor por Hash**

#### **GET /api/server/{server_hash}**

Consulta informações de um servidor específico usando o hash como identificação.

**Exemplo:**
```
GET /api/server/918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d
```

**Resposta (200 OK):**
```json
{
  "success": true,
  "data": {
    "server": {
      "id": 1,
      "server_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d",
      "server_name": "Meu Servidor SCUM",
      "version": "3.0.0",
      "max_players": 64,
      "current_players": 32,
      "is_active": true,
      "last_sync": "2025-01-15T10:30:00Z",
      "created_at": "2025-01-10T08:00:00Z"
    },
    "players": {
      "total": 150,
      "online": 32,
      "list": [
        {
          "steam_id": "76561198012345678",
          "name": "PlayerName",
          "fame": 15000,
          "is_online": true,
          "last_seen": "2025-01-15T10:30:00Z"
        }
      ]
    },
    "rankings": {
      "survival": [
        {
          "steam_id": "76561198012345678",
          "name": "PlayerName",
          "rank": 1,
          "score": 95.5
        }
      ],
      "kills": [...],
      "lockpicking": [...],
      "fishing": [...]
    }
  }
}
```

**Resposta (404 Not Found):**
```json
{
  "success": false,
  "error": "Servidor não encontrado"
}
```

---

### **Endpoints Adicionais de Consulta**

#### **GET /api/server/{server_hash}/players**

Retorna apenas a lista de jogadores do servidor.

**Query Parameters:**
- `online_only` (boolean): Se `true`, retorna apenas jogadores online
- `limit` (int): Limite de resultados (padrão: 100)
- `offset` (int): Offset para paginação

**Exemplo:**
```
GET /api/server/{server_hash}/players?online_only=true&limit=50
```

---

#### **GET /api/server/{server_hash}/rankings**

Retorna apenas os rankings do servidor.

**Query Parameters:**
- `type` (string): Tipo de ranking (`survival`, `kills`, `lockpicking`, `fishing`)
- `limit` (int): Limite de resultados (padrão: 100)

**Exemplo:**
```
GET /api/server/{server_hash}/rankings?type=survival&limit=20
```

---

#### **GET /api/server/{server_hash}/info**

Retorna apenas informações básicas do servidor (sem jogadores/rankings).

**Resposta:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "server_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d",
    "server_name": "Meu Servidor SCUM",
    "version": "3.0.0",
    "max_players": 64,
    "current_players": 32,
    "is_active": true,
    "last_sync": "2025-01-15T10:30:00Z"
  }
}
```

---

#### **GET /api/servers**

Lista todos os servidores cadastrados.

**Query Parameters:**
- `active_only` (boolean): Se `true`, retorna apenas servidores ativos
- `limit` (int): Limite de resultados
- `offset` (int): Offset para paginação

**Resposta:**
```json
{
  "success": true,
  "data": {
    "total": 10,
    "servers": [
      {
        "id": 1,
        "server_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d",
        "server_name": "Meu Servidor SCUM",
        "current_players": 32,
        "max_players": 64,
        "is_active": true,
        "last_sync": "2025-01-15T10:30:00Z"
      }
    ]
  }
}
```

---

### **Implementação dos Endpoints de Consulta**

```python
# Gestão/app/routes/servers.py

from flask import Blueprint, request, jsonify
from app.models.server import Server, ServerPlayer, ServerRanking
from datetime import datetime

bp = Blueprint('servers', __name__, url_prefix='/api')

@bp.route('/server/<server_hash>', methods=['GET'])
def get_server_by_hash(server_hash):
    """
    Consultar servidor por hash
    
    GET /api/server/{server_hash}
    """
    # Validar formato do hash
    if len(server_hash) != 64 or not all(c in '0123456789abcdef' for c in server_hash.lower()):
        return jsonify({
            'success': False,
            'error': 'Formato de hash inválido'
        }), 400
    
    # Buscar servidor
    server = Server.query.filter_by(server_hash=server_hash).first()
    
    if not server:
        return jsonify({
            'success': False,
            'error': 'Servidor não encontrado'
        }), 404
    
    # Buscar jogadores
    players = ServerPlayer.query.filter_by(server_id=server.id).all()
    players_data = [{
        'steam_id': p.steam_id,
        'name': p.player_name,
        'fame': p.fame,
        'is_online': p.is_online,
        'last_seen': p.last_seen.isoformat() if p.last_seen else None
    } for p in players]
    
    # Buscar rankings
    rankings_data = {}
    ranking_types = ['survival', 'kills', 'lockpicking', 'fishing']
    
    for ranking_type in ranking_types:
        rankings = ServerRanking.query.filter_by(
            server_id=server.id,
            ranking_type=ranking_type
        ).order_by(ServerRanking.rank.asc()).limit(100).all()
        
        rankings_data[ranking_type] = [{
            'steam_id': r.steam_id,
            'name': r.player_name,
            'rank': r.rank,
            'score': r.score
        } for r in rankings]
    
    return jsonify({
        'success': True,
        'data': {
            'server': {
                'id': server.id,
                'server_hash': server.server_hash,
                'server_name': server.server_name,
                'version': server.version,
                'max_players': server.max_players,
                'current_players': server.current_players,
                'is_active': server.is_active,
                'last_sync': server.last_sync.isoformat() if server.last_sync else None,
                'created_at': server.created_at.isoformat() if server.created_at else None
            },
            'players': {
                'total': len(players_data),
                'online': sum(1 for p in players_data if p['is_online']),
                'list': players_data
            },
            'rankings': rankings_data
        }
    }), 200


@bp.route('/server/<server_hash>/players', methods=['GET'])
def get_server_players(server_hash):
    """
    Consultar jogadores de um servidor
    
    GET /api/server/{server_hash}/players?online_only=true&limit=50
    """
    server = Server.query.filter_by(server_hash=server_hash).first()
    
    if not server:
        return jsonify({
            'success': False,
            'error': 'Servidor não encontrado'
        }), 404
    
    # Query parameters
    online_only = request.args.get('online_only', 'false').lower() == 'true'
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    # Query base
    query = ServerPlayer.query.filter_by(server_id=server.id)
    
    if online_only:
        query = query.filter_by(is_online=True)
    
    # Aplicar paginação
    players = query.order_by(ServerPlayer.fame.desc()).offset(offset).limit(limit).all()
    
    players_data = [{
        'steam_id': p.steam_id,
        'name': p.player_name,
        'fame': p.fame,
        'is_online': p.is_online,
        'last_seen': p.last_seen.isoformat() if p.last_seen else None
    } for p in players]
    
    return jsonify({
        'success': True,
        'data': {
            'total': len(players_data),
            'players': players_data
        }
    }), 200


@bp.route('/server/<server_hash>/rankings', methods=['GET'])
def get_server_rankings(server_hash):
    """
    Consultar rankings de um servidor
    
    GET /api/server/{server_hash}/rankings?type=survival&limit=20
    """
    server = Server.query.filter_by(server_hash=server_hash).first()
    
    if not server:
        return jsonify({
            'success': False,
            'error': 'Servidor não encontrado'
        }), 404
    
    ranking_type = request.args.get('type')
    limit = int(request.args.get('limit', 100))
    
    if ranking_type:
        # Ranking específico
        rankings = ServerRanking.query.filter_by(
            server_id=server.id,
            ranking_type=ranking_type
        ).order_by(ServerRanking.rank.asc()).limit(limit).all()
        
        rankings_data = [{
            'steam_id': r.steam_id,
            'name': r.player_name,
            'rank': r.rank,
            'score': r.score
        } for r in rankings]
        
        return jsonify({
            'success': True,
            'data': {
                'type': ranking_type,
                'rankings': rankings_data
            }
        }), 200
    else:
        # Todos os rankings
        rankings_data = {}
        ranking_types = ['survival', 'kills', 'lockpicking', 'fishing']
        
        for rt in ranking_types:
            rankings = ServerRanking.query.filter_by(
                server_id=server.id,
                ranking_type=rt
            ).order_by(ServerRanking.rank.asc()).limit(limit).all()
            
            rankings_data[rt] = [{
                'steam_id': r.steam_id,
                'name': r.player_name,
                'rank': r.rank,
                'score': r.score
            } for r in rankings]
        
        return jsonify({
            'success': True,
            'data': rankings_data
        }), 200


@bp.route('/server/<server_hash>/info', methods=['GET'])
def get_server_info(server_hash):
    """
    Consultar informações básicas do servidor
    
    GET /api/server/{server_hash}/info
    """
    server = Server.query.filter_by(server_hash=server_hash).first()
    
    if not server:
        return jsonify({
            'success': False,
            'error': 'Servidor não encontrado'
        }), 404
    
    return jsonify({
        'success': True,
        'data': {
            'id': server.id,
            'server_hash': server.server_hash,
            'server_name': server.server_name,
            'version': server.version,
            'max_players': server.max_players,
            'current_players': server.current_players,
            'is_active': server.is_active,
            'last_sync': server.last_sync.isoformat() if server.last_sync else None,
            'created_at': server.created_at.isoformat() if server.created_at else None
        }
    }), 200


@bp.route('/servers', methods=['GET'])
def list_servers():
    """
    Listar todos os servidores
    
    GET /api/servers?active_only=true&limit=10&offset=0
    """
    # Query parameters
    active_only = request.args.get('active_only', 'false').lower() == 'true'
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    # Query base
    query = Server.query
    
    if active_only:
        query = query.filter_by(is_active=True)
    
    # Contar total
    total = query.count()
    
    # Aplicar paginação
    servers = query.order_by(Server.last_sync.desc()).offset(offset).limit(limit).all()
    
    servers_data = [{
        'id': s.id,
        'server_hash': s.server_hash,
        'server_name': s.server_name,
        'current_players': s.current_players,
        'max_players': s.max_players,
        'is_active': s.is_active,
        'last_sync': s.last_sync.isoformat() if s.last_sync else None
    } for s in servers]
    
    return jsonify({
        'success': True,
        'data': {
            'total': total,
            'servers': servers_data
        }
    }), 200
```

---

## 🌐 Arquitetura de Rede e Firewall

### **Arquitetura com POST (SSM Backend envia para Gestão)**

```
┌─────────────────┐   1. GET /ready?hash    ┌──────────────┐
│  SSM Backend     │ ─────────────────────> │   Gestão      │
│  (Servidor 1)   │                         │  (Servidor    │
│                 │   2. POST /sync         │   Central)    │
│  Porta: 3000    │ ─────────────────────> │  Porta: 5000  │
│  (LOCAL)        │                         │  (PÚBLICO)    │
└─────────────────┘                         └──────────────┘
       │                                              │
       │                                              │
       │                                              │
┌─────────────────┐                            ┌──────────────┐
│  SSM Backend     │ ─────────────────────> │               │
│  (Servidor 2)   │    GET /ready + POST    │               │
│  Porta: 3000    │                         │               │
│  (LOCAL)        │                         │               │
└─────────────────┘                         └──────────────┘
```

### **✅ NÃO Precisa Abrir Portas no SSM Backend!**

**Por quê?**
- O **SSM Backend** faz requisições **OUTBOUND** (saída) para o Gestão
- Requisições de saída **NÃO precisam** de portas abertas no firewall
- O SSM Backend funciona como um **cliente** que envia dados

**O que precisa:**
- ✅ **Gestão** precisa ter porta **5000** (ou configurada) aberta no firewall
- ✅ **SSM Backend** precisa ter acesso à internet (para fazer requisições HTTP)
- ❌ **NÃO precisa** abrir porta 3000 do SSM Backend no firewall
- ❌ **NÃO precisa** de IP público ou port forwarding no SSM Backend

### **Configuração de Rede**

#### **1. No SSM Backend (Servidores que serão consultados)**

**Cada SSM Backend precisa:**
- ✅ Porta **3000** (ou porta configurada) aberta no firewall
- ✅ IP público ou port forwarding configurado
- ✅ Endpoint `/api/server/{server_hash}` acessível publicamente

**Exemplo de URLs:**
```
http://192.168.1.100:3000/api/server/{hash}  # IP local (se Gestão estiver na mesma rede)
http://servidor1.seudominio.com:3000/api/server/{hash}  # Domínio
http://200.150.100.50:3000/api/server/{hash}  # IP público
```

**Firewall do SSM Backend:**
```bash
# Linux (UFW)
sudo ufw allow 3000/tcp

# Linux (iptables)
iptables -A INPUT -p tcp --dport 3000 -j ACCEPT

# Windows Firewall
# Permitir porta 3000 TCP nas regras de entrada
```

**Modem/Router:**
- ✅ Configurar **Port Forwarding** da porta 3000 para o IP interno do SSM Backend
- ✅ Ou colocar SSM Backend em DMZ (menos seguro)

#### **2. No Gestão (Servidor Central que faz consultas)**

**Gestão precisa:**
- ✅ Acesso à internet para fazer requisições HTTP
- ✅ Lista de URLs/IPs dos SSM Backends cadastrados

**Configuração no Gestão:**
```python
# Gestão/app/config.py ou banco de dados

servers = [
    {
        "server_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d",
        "url": "http://servidor1.seudominio.com:3000",
        "name": "Servidor SCUM 1"
    },
    {
        "server_hash": "outro_hash_aqui...",
        "url": "http://200.150.100.50:3000",
        "name": "Servidor SCUM 2"
    }
]
```

**Firewall do Gestão:**
- ✅ Permitir conexões de saída (outbound) na porta 80/443
- ❌ Não precisa abrir portas de entrada (a menos que tenha interface web)

### **Arquitetura Escolhida: POST com Handshake**

**Esta é a arquitetura que será implementada:**
- SSM Backend envia dados para o Gestão usando POST
- Sistema de handshake: SSM pergunta se Gestão está pronto antes de enviar
- Se Gestão não estiver pronto, SSM aguarda e tenta novamente

**Vantagens:**
- ✅ **NÃO precisa** abrir portas no SSM Backend
- ✅ **NÃO precisa** de IP público ou port forwarding
- ✅ Gestão controla carga (pode recusar quando ocupado)
- ✅ Retry automático inteligente
- ✅ Mais seguro (apenas Gestão expõe portas)
- ✅ SSM Backend pode estar atrás de NAT/firewall

**Fluxo de Funcionamento:**
1. SSM Backend verifica periodicamente (a cada 4 horas)
2. SSM faz GET `/api/servers/ready?server_hash={hash}`
3. Se Gestão responder `ready: true`, SSM envia POST `/api/servers/sync`
4. Se Gestão responder `ready: false`, SSM aguarda `retry_after` segundos e tenta novamente
5. Se Gestão estiver offline, SSM aguarda e tenta depois

**Soluções implementadas:**
- ✅ Handshake antes de enviar (evita sobrecarga)
- ✅ Retry automático com backoff
- ✅ Rate limiting no Gestão
- ✅ Timeout nas requisições
- ✅ Logs de tentativas

### **Exemplo de Configuração Completa**

#### **1. Gestão (servidor que recebe dados)**

**Abrir porta no firewall:**
```bash
# Linux (UFW)
sudo ufw allow 5000/tcp

# Linux (iptables)
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT

# Windows Firewall
# Configurar regra de entrada para porta 5000 TCP
```

**Configurar Flask:**
```python
# Gestão/app/__init__.py
app.run(host='0.0.0.0', port=5000, debug=False)  # Escuta em todas as interfaces
```

#### **2. SSM Backend (servidor que envia dados)**

**NÃO precisa:**
- ❌ Abrir porta no firewall
- ❌ Configurar port forwarding
- ❌ IP público

**Apenas precisa:**
- ✅ Acesso à internet
- ✅ URL do Gestão configurada

**Configuração:**
```python
# Backend/data/config.json
{
  "communication": {
    "gestao": {
      "url": "https://gestao.seudominio.com",
      "enabled": true,
      "sync_interval": 14400,  # 4 horas
      "api_key": "sua_api_key_aqui",
      "handshake_timeout": 5,  # segundos
      "sync_timeout": 30,  # segundos
      "max_retry_delay": 3600  # 1 hora máximo
    }
  }
}
```

**Testar conectividade do SSM Backend:**
```python
# No SSM Backend, testar se consegue acessar o Gestão
import requests

gestao_url = "https://gestao.seudominio.com"

try:
    response = requests.get(
        f"{gestao_url}/api/servers/ready",
        params={"server_hash": "seu_hash_aqui"},
        timeout=5
    )
    print(f"✅ Conectividade OK: {response.status_code}")
    print(f"Resposta: {response.json()}")
except Exception as e:
    print(f"❌ Erro de conectividade: {e}")
```

---

## 📋 Fluxo de Cadastro de Servidor

### **1. Obter Hash do SSM Backend**

**Opção A: Via endpoint no SSM Backend (Recomendado)**
```
GET /api/server/hash
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "server_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d",
    "server_name": "Meu Servidor SCUM",
    "version": "3.0.0"
  }
}
```

**Opção B: Via arquivo de configuração**
- SSM Backend salva hash em `data/hardware_fingerprint.json`
- Admin lê o arquivo e copia o hash

**Opção C: Via interface do SSM Backend**
- Interface mostra hash na tela de configurações
- Admin copia o hash

### **2. Cadastrar Servidor no Gestão**

**Interface Admin do Gestão:**
```
1. Admin acessa: /admin/servers/new
2. Preenche formulário:
   - Server Hash: [campo para colar hash]
   - Server Name: [opcional]
3. Clica em "Cadastrar"
4. Gestão:
   - Valida formato do hash
   - Gera API key única
   - Salva no banco
   - Mostra API key para o admin
5. Admin copia API key
```

**Endpoint de Cadastro (Admin):**
```
POST /admin/servers
Body: {
  "server_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d",
  "server_name": "Meu Servidor SCUM"
}

Resposta: {
  "success": true,
  "data": {
    "server_id": 1,
    "server_hash": "918aabd...",
    "api_key": "abc123xyz789",  // ← IMPORTANTE: Admin precisa copiar
    "message": "Servidor cadastrado com sucesso"
  }
}
```

### **3. Configurar API Key no SSM Backend**

**No arquivo `config.json` (usar seção `licensing` existente):**
```json
{
  "licensing": {
    "enabled": false,
    "server_url": "http://localhost:8000",
    "validation_interval_seconds": 14400,
    "hardware_check_interval_seconds": 3600,
    "cache_ttl_seconds": 14400,
    "require_internet": true,
    "block_on_invalid": true,
    "timeout_seconds": 10,
    "retry_attempts": 3,
    "retry_delay_seconds": 30,
    "description": "Sistema de licenciamento com hardware fingerprint - Configure server_url e defina enabled=true para ativar. Endpoint: POST http://localhost:8000/api/v1/validate (TESTE) | https://www.scumsm.com/api/v1/validate (PRODUÇÃO)",
    
    // Campos adicionais para sincronização com Gestão
    "gestao_url": "https://gestao.seudominio.com",
    "gestao_api_key": "",  // ← OBRIGATÓRIO: API key gerada pelo Gestão (copiar após cadastrar servidor)
    "gestao_enabled": true,
    "gestao_sync_interval_seconds": 14400,  // 4 horas
    "gestao_handshake_timeout_seconds": 5,
    "gestao_sync_timeout_seconds": 30,
    "gestao_max_retry_delay_seconds": 3600,
    "gestao_max_retries": 3
  }
}
```

**Estrutura completa:**
```json
{
  "licensing": {
    "enabled": false,
    "server_url": "http://localhost:8000",
    "validation_interval_seconds": 14400,
    "hardware_check_interval_seconds": 3600,
    "cache_ttl_seconds": 14400,
    "require_internet": true,
    "block_on_invalid": true,
    "timeout_seconds": 10,
    "retry_attempts": 3,
    "retry_delay_seconds": 30,
    "description": "Sistema de licenciamento com hardware fingerprint - Configure server_url e defina enabled=true para ativar. Endpoint: POST http://localhost:8000/api/v1/validate (TESTE) | https://www.scumsm.com/api/v1/validate (PRODUÇÃO)",
    
    // Campos para sincronização com Gestão (mesma seção)
    "gestao_url": "https://gestao.seudominio.com",
    "gestao_api_key": "ssm_2d9ba653192f1a872fbef6583485c50fd6265384ace80ecf222727cc41c4ac4c",
    "gestao_enabled": true,
    "gestao_sync_interval_seconds": 14400,  // 4 horas
    "gestao_handshake_timeout_seconds": 5,
    "gestao_sync_timeout_seconds": 30,
    "gestao_max_retry_delay_seconds": 3600,
    "gestao_max_retries": 3
  }
}
```

**Vantagens de usar a seção `licensing`:**
- ✅ API Key já vem do sistema de licenças
- ✅ Mantém tudo relacionado a autenticação/licenciamento junto
- ✅ Não cria nova seção desnecessária
- ✅ Mais organizado e lógico

**Campos obrigatórios:**
- ✅ `api_key`: **OBRIGATÓRIO** - Deve ser preenchido após cadastrar servidor no Gestão
- ✅ `url`: URL do servidor Gestão (ex: `https://gestao.seudominio.com`)

**Campos opcionais (com defaults):**
- `enabled`: `false` (padrão) - Ativar/desativar sincronização
- `sync_interval_seconds`: `14400` (4 horas) - Intervalo entre sincronizações
- `handshake_timeout_seconds`: `5` - Timeout do handshake
- `sync_timeout_seconds`: `30` - Timeout da sincronização
- `max_retry_delay_seconds`: `3600` (1 hora) - Delay máximo entre tentativas
- `max_retries`: `3` - Número máximo de tentativas

### **4. Testar Sincronização**

**SSM Backend tenta sincronizar:**
```
1. GET /api/servers/ready?server_hash={hash}
   → Gestão verifica se servidor está cadastrado
   → Se sim, retorna {ready: true}

2. POST /api/servers/sync
   → Gestão valida hash + api_key
   → Se válido, sincroniza dados
   → Retorna {success: true}
```

---

## 📊 Planejamento Detalhado: Coleta e Estruturação de Dados de Ranking

### **Análise dos Dados Disponíveis**

O SSM Backend já possui endpoints que coletam dados de ranking da tabela `rankings` do `SSM.db`:

#### **1. Endpoint Existente: GET /api/rankings**
- **Categorias disponíveis:**
  - `kills` - Total de kills
  - `deaths` - Total de deaths
  - `kdr` - Kill/Death Ratio
  - `longest_shot` - Maior distância de tiro
  - `lockpick_basic_rate` - Taxa de sucesso lockpick básico
  - `lockpick_medium_rate` - Taxa de sucesso lockpick médio
  - `lockpick_advanced_rate` - Taxa de sucesso lockpick avançado
  - `lockpick_veryeasy_rate` - Taxa de sucesso lockpick muito fácil
  - `lockpick_diallock_rate` - Taxa de sucesso lockpick diallock
  - `suicides` - Total de suicídios
  - `defecation` - Maior defecação
  - `vehicles` - Veículos destruídos
  - `hunting` - Animais mortos
  - `melee` - Nocautes em jogadores
  - `headshots` - Total de headshots
  - `survival_time` - Minutos sobrevividos
  - `overdoses` - Total de overdoses
  - `weight` - Maior peso carregado
  - `fame` - Total de fama

#### **2. Estrutura da Tabela `rankings`**
```sql
CREATE TABLE rankings (
    steam_id TEXT PRIMARY KEY,
    player_name TEXT,
    kills INTEGER,
    deaths INTEGER,
    kdr REAL,
    longest_shot_distance REAL,
    longest_shot_weapon TEXT,
    longest_shot_timestamp TEXT,
    suicides INTEGER,
    lockpick_basic_success INTEGER,
    lockpick_basic_fails INTEGER,
    lockpick_basic_total INTEGER,
    lockpick_basic_rate REAL,
    lockpick_medium_success INTEGER,
    lockpick_medium_fails INTEGER,
    lockpick_medium_total INTEGER,
    lockpick_medium_rate REAL,
    lockpick_advanced_success INTEGER,
    lockpick_advanced_fails INTEGER,
    lockpick_advanced_total INTEGER,
    lockpick_advanced_rate REAL,
    lockpick_veryeasy_success INTEGER,
    lockpick_veryeasy_fails INTEGER,
    lockpick_veryeasy_total INTEGER,
    lockpick_veryeasy_rate REAL,
    lockpick_diallock_success INTEGER,
    lockpick_diallock_fails INTEGER,
    lockpick_diallock_total INTEGER,
    lockpick_diallock_rate REAL,
    lockpick_other_success INTEGER,
    lockpick_other_fails INTEGER,
    lockpick_other_total INTEGER,
    lockpick_other_rate REAL,
    vehicles_destroyed INTEGER,
    highest_defecation INTEGER,
    animals_killed INTEGER,
    players_knocked_out INTEGER,
    headshots INTEGER,
    minutes_survived INTEGER,
    overdoses INTEGER,
    highest_weight_carried REAL,
    total_fame REAL,
    last_updated TEXT
);
```

### **Estrutura de Dados para Envio ao Gestão**

#### **Rankings Principais a Enviar**

Baseado no planejamento, enviaremos os seguintes tipos de ranking:

1. **Kills** - Top Killers (ordenado por kills DESC, kdr DESC)
2. **Survival** - Tempo de Sobrevivência (ordenado por minutes_survived DESC)
3. **Lockpicking** - Taxa Média de Sucesso (média das taxas de todos os tipos)
4. **Fishing/Hunting** - Animais Mortos (ordenado por animals_killed DESC)

#### **Formato do Payload de Rankings**

```json
{
  "rankings": {
    "kills": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerName",
        "score": 150,  // kills
        "kdr": 2.5,
        "deaths": 60
      },
      // ... até 100 registros
    ],
    "survival": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerName",
        "score": 125000,  // minutes_survived
        "fame": 50000
      },
      // ... até 100 registros
    ],
    "lockpicking": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerName",
        "score": 85.5,  // taxa média (0-100)
        "basic_rate": 90.0,
        "medium_rate": 85.0,
        "advanced_rate": 80.0
      },
      // ... até 100 registros
    ],
    "fishing": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerName",
        "score": 250  // animals_killed
      },
      // ... até 100 registros
    ]
  }
}
```

### **Estratégia de Coleta de Dados**

#### **1. Método `_get_rankings_data()`**

**Fonte:** Tabela `rankings` do `SSM.db`

**Queries SQL:**

```sql
-- 1. Ranking de Kills (Top 100)
SELECT steam_id, player_name, kills, deaths, kdr
FROM rankings
WHERE kills > 0
ORDER BY kills DESC, kdr DESC
LIMIT 100

-- 2. Ranking de Survival (Top 100)
SELECT steam_id, player_name, minutes_survived, total_fame
FROM rankings
WHERE minutes_survived > 0
ORDER BY minutes_survived DESC
LIMIT 100

-- 3. Ranking de Lockpicking (Top 100)
SELECT steam_id, player_name,
       (lockpick_basic_rate + lockpick_medium_rate + 
        lockpick_advanced_rate + lockpick_veryeasy_rate + 
        lockpick_diallock_rate) / 5.0 as avg_rate,
       lockpick_basic_rate, lockpick_medium_rate, 
       lockpick_advanced_rate
FROM rankings
WHERE (lockpick_basic_rate + lockpick_medium_rate + 
       lockpick_advanced_rate + lockpick_veryeasy_rate + 
       lockpick_diallock_rate) > 0
ORDER BY avg_rate DESC
LIMIT 100

-- 4. Ranking de Fishing/Hunting (Top 100)
SELECT steam_id, player_name, animals_killed as fishing_score
FROM rankings
WHERE animals_killed > 0
ORDER BY animals_killed DESC
LIMIT 100
```

**Observações:**
- ✅ Limite de 100 registros por tipo de ranking (evita payload muito grande)
- ✅ Filtra apenas jogadores com valores > 0 (não envia dados vazios)
- ✅ Ordenação específica para cada tipo de ranking
- ✅ Inclui campos adicionais relevantes (kdr, fame, etc)

#### **2. Método `_get_players_data()`**

**Fonte:** Tabelas `players_online` e `rankings` do `SSM.db`

**Query SQL:**

```sql
-- Buscar todos os jogadores (online e offline)
SELECT 
    po.steam_id,
    COALESCE(po.player_name, r.player_name, 'Unknown') as player_name,
    COALESCE(r.total_fame, 0) as fame,
    CASE WHEN po.status = 'online' THEN 1 ELSE 0 END as is_online,
    po.last_activity as last_seen
FROM players_online po
LEFT JOIN rankings r ON po.steam_id = r.steam_id
UNION
SELECT 
    r.steam_id,
    r.player_name,
    COALESCE(r.total_fame, 0) as fame,
    0 as is_online,
    NULL as last_seen
FROM rankings r
WHERE r.steam_id NOT IN (SELECT steam_id FROM players_online)
ORDER BY fame DESC
LIMIT 1000
```

**Formato de Saída:**

```json
{
  "players": [
    {
      "steam_id": "76561198012345678",
      "name": "PlayerName",
      "fame": 50000,
      "is_online": true,
      "last_seen": "2025-01-15T10:30:00Z"
    },
    // ... até 1000 registros
  ]
}
```

**Observações:**
- ✅ Limite de 1000 jogadores (evita payload muito grande)
- ✅ Inclui jogadores online e offline
- ✅ Usa `players_online` para status atual
- ✅ Usa `rankings` como fallback para jogadores offline
- ✅ Ordena por fama (mais relevantes primeiro)

#### **3. Método `_get_server_info()`**

**Fonte:** `config.json` e contagem de jogadores online

**Estrutura:**

```json
{
  "server_info": {
    "name": "Meu Servidor SCUM",  // communication.server_name
    "version": "3.0.0",            // Versão do SSM Backend
    "max_players": 64,             // server.max_players
    "current_players": 32          // Contagem de players_online WHERE status='online'
  }
}
```

**Observações:**
- ✅ Nome do servidor vem de `config.communication.server_name`
- ✅ Versão é fixa "3.0.0" (pode ser obtida dinamicamente depois)
- ✅ Max players vem de `config.server.max_players`
- ✅ Current players é contagem em tempo real de `players_online`

### **Otimizações e Limites**

#### **Limites de Dados**

1. **Rankings:** Máximo 100 registros por tipo (4 tipos = 400 registros máximo)
2. **Players:** Máximo 1000 jogadores
3. **Payload Total:** Estimativa ~500KB-1MB (dependendo do número de jogadores)

#### **Estratégias de Otimização**

1. **Filtragem Inteligente:**
   - Enviar apenas jogadores com dados relevantes (fame > 0 ou online)
   - Rankings apenas com valores > 0

2. **Compressão (Futuro):**
   - Considerar gzip compression no payload
   - Reduzir tamanho em ~70-80%

3. **Incremental Sync (Futuro):**
   - Enviar apenas mudanças desde última sincronização
   - Reduzir payload significativamente

4. **Cache Local:**
   - Cachear dados coletados por alguns segundos
   - Evitar múltiplas queries durante handshake

### **Tratamento de Erros**

#### **Cenários de Erro**

1. **Banco de dados não encontrado:**
   - Retornar arrays vazios `[]` ou `{}`
   - Logar erro mas não falhar sincronização

2. **Query SQL falha:**
   - Try/catch em cada query
   - Continuar com outros rankings mesmo se um falhar
   - Logar erro específico

3. **Dados inválidos:**
   - Validar steam_id não nulo
   - Validar nome não vazio
   - Usar valores padrão para campos opcionais

4. **Timeout na coleta:**
   - Limitar tempo de coleta (ex: 10 segundos máximo)
   - Enviar dados parciais se timeout ocorrer

### **Formato Completo do Payload**

```json
{
  "server_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d",
  "api_key": "ssm_0e6892b077c28a0876ea8d0f5d2d8beedfa66c604ddec25d6d7a403ba5d098d5",
  "server_info": {
    "name": "Meu Servidor SCUM",
    "version": "3.0.0",
    "max_players": 64,
    "current_players": 32
  },
  "players": [
    {
      "steam_id": "76561198012345678",
      "name": "PlayerName",
      "fame": 50000,
      "is_online": true,
      "last_seen": "2025-01-15T10:30:00Z"
    }
  ],
  "rankings": {
    "kills": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerName",
        "score": 150,
        "kdr": 2.5,
        "deaths": 60
      }
    ],
    "survival": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerName",
        "score": 125000,
        "fame": 50000
      }
    ],
    "lockpicking": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerName",
        "score": 85.5,
        "basic_rate": 90.0,
        "medium_rate": 85.0,
        "advanced_rate": 80.0
      }
    ],
    "fishing": [
      {
        "steam_id": "76561198012345678",
        "name": "PlayerName",
        "score": 250
      }
    ]
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## 🎯 Próximos Passos

1. ✅ **Planejamento** (este documento)
2. ⏳ **Criar endpoint GET /api/server/hash no SSM Backend** (para obter hash)
3. ⏳ **Implementar modelo de dados no Gestão**
4. ⏳ **Criar interface de cadastro de servidor no Gestão** (admin)
5. ⏳ **Criar endpoint GET /api/servers/ready no Gestão** (handshake)
6. ⏳ **Criar endpoint POST /api/servers/sync no Gestão** (sincronização)
7. ⏳ **Criar GestaoSyncService no Backend** (com métodos de coleta planejados acima)
8. ⏳ **Configurar sincronização periódica**
9. ⏳ **Criar interface no Gestão para visualizar dados**
10. ⏳ **Testes e validação**

---

## ❓ Decisões Pendentes

1. **Frequência de sincronização?**
   - ✅ **Decisão**: A cada 4 horas (14400 segundos)
   - Reduz carga no Gestão
   - Rankings e dados de jogadores não precisam ser atualizados em tempo real
   - Alternativa: A cada 5 minutos (mais atualizado, mais carga)

2. **O que fazer quando hash mudar?**
   - Proposta: Atualizar hash mantendo histórico
   - Alternativa: Criar novo servidor

3. **Retenção de dados?**
   - Quanto tempo manter jogadores offline?
   - Quanto tempo manter rankings antigos?

4. **API Key:**
   - ✅ **Decisão**: Gerada pelo Gestão quando servidor é cadastrado
   - Admin cadastra servidor no Gestão
   - Gestão gera API key única (ex: UUID ou hash aleatório)
   - Admin copia API key e configura no SSM Backend
   - SSM Backend envia api_key nas sincronizações
   - Gestão valida api_key comparando com a cadastrada

5. **Cadastro prévio vs Auto-registro:**
   - ✅ **Decisão**: Cadastro prévio obrigatório
   - Servidor DEVE estar cadastrado no Gestão ANTES de sincronizar
   - Admin cadastra servidor informando o hash
   - Gestão gera e retorna API key
   - SSM Backend configura API key e pode sincronizar
   - Se servidor não cadastrado → Gestão REJEITA (403)

---

## 📝 Notas Importantes

### **Identificação do Servidor**

- O **`server_hash`** (equipment_hash/hardware fingerprint) é o **identificador único**
- Gestão identifica servidor fazendo: `Server.query.filter_by(server_hash={hash})`
- **Servidor DEVE estar cadastrado ANTES de sincronizar**
- Hash é enviado no body do POST: `{"server_hash": "...", ...}`

### **Fluxo de Cadastro e Identificação**

#### **1. Cadastro do Servidor (Admin no Gestão)**

```
Admin acessa Gestão → Cadastra Servidor
  ↓
Informa:
  - server_hash (obtido do SSM Backend)
  - server_name (opcional, pode atualizar depois)
  ↓
Gestão:
  - Cria registro na tabela Server
  - Gera API key única (ex: UUID)
  - Retorna API key ao admin
  ↓
Admin copia API key e configura no SSM Backend
```

#### **2. Sincronização (SSM Backend → Gestão)**

```
SSM Backend envia POST:
{
  "server_hash": "918aabd12dc60d8432ab952f8eab6557a5b8b14066953e26516fab6f1ff0c54d",
  "api_key": "abc123xyz789",  // API key gerada pelo Gestão
  "server_info": {"name": "Meu Servidor", ...},
  ...
}
  ↓
Gestão busca servidor:
server = Server.query.filter_by(server_hash="918aabd...").first()
  ↓
Se não encontrar:
  → REJEITA (403 Forbidden)
  → Erro: "Servidor não cadastrado"
  ↓
Se encontrar:
  → Valida api_key (deve ser igual ao cadastrado)
  → Se inválida → REJEITA (401 Unauthorized)
  → Se válida → Sincroniza dados
```

### **Geração da API Key**

**Opções de geração:**
1. **UUID v4** (recomendado):
   ```python
   import uuid
   api_key = str(uuid.uuid4())
   # Exemplo: "550e8400-e29b-41d4-a716-446655440000"
   ```

2. **Hash aleatório**:
   ```python
   import secrets
   api_key = secrets.token_urlsafe(32)
   # Exemplo: "abc123xyz789..."
   ```

3. **Hash do server_hash + timestamp**:
   ```python
   import hashlib
   api_key = hashlib.sha256(f"{server_hash}{timestamp}".encode()).hexdigest()[:32]
   ```

### **Mudança de Hash (Hardware Mudou)**

- Se o hardware mudar, o hash muda
- SSM Backend enviará novo hash
- Gestão não encontrará servidor (hash diferente)
- **Solução**: Buscar servidor por `api_key` também
  ```python
  # Se não encontrar por hash, buscar por api_key
  server = Server.query.filter_by(server_hash=new_hash).first()
  if not server:
      server = Server.query.filter_by(api_key=api_key).first()
      if server:
          # Atualizar hash mantendo histórico
          server.server_hash = new_hash
  ```

### **API Key**

- **API key é gerada pelo Gestão** quando servidor é cadastrado
- Admin cadastra servidor → Gestão gera API key → Admin configura no SSM Backend
- SSM Backend envia `api_key` no POST junto com o hash
- Gestão valida `api_key` comparando com a cadastrada
- Se `api_key` inválida → REJEITA (401 Unauthorized)
- Pode ser usada como fallback se hash mudar (buscar servidor por api_key)
