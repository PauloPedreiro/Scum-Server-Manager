# Respostas para o Dev do Gestao - Endpoints de Veiculos (Player App)

Data: 2026-02-19

---

## 1) `status_text` sempre vem em pt-BR? Vai suportar locale?

**Sim, e hardcoded pt-BR.** O mapa e fixo no backend:

```python
status_map = {0: "Ativo", 1: "Inativo", 2: "Desaparecido", 3: "Destruido"}
```

**Nao ha plano de suporte a locale no SSM.**

### Recomendacao

- Usar o campo `status` (inteiro 0/1/2/3) como **fonte de verdade** no client.
- Traduzir no frontend conforme o locale do usuario.
- `status_text` existe como conveniencia para debug/admin, mas o client nao deve depender dele para exibicao final.
- Futuramente pode ser removido do contrato player-scoped se gerar confusao.

---

## 2) Qual a diferenca exata entre `entity_id` e `vehicle_entity_id`?

Sao IDs diferentes na hierarquia do SCUM:

| Campo               | O que e                                                                 |
|---------------------|-------------------------------------------------------------------------|
| `entity_id`         | ID do **container** (compartimento de carga) dentro do veiculo. E a PK da tabela `vehicle_current_ownership`. Aparece nos logs de `chest_ownership`. |
| `vehicle_entity_id` | ID da **entidade do veiculo em si** (entidade pai no `vehicle_spawner` do SCUM.db). E o identificador real do veiculo no mundo do jogo. |

### Na pratica

Um veiculo pode ter **multiplos containers** (inventario principal, expansao, rack de armazenamento). O SSM deduplica e mantem 1 registro por `entity_id` (container principal), mas `vehicle_entity_id` e o que identifica unicamente o veiculo.

### Recomendacao para o frontend

- Usar **`vehicle_entity_id`** como identificador do veiculo em todas as telas.
- E ele que vai na URL: `GET /api/player/vehicles/<vehicle_entity_id>`.
- `entity_id` e `container_class` sao detalhes internos — uteis para admin/debug, nao para o jogador final.

---

## 3) `updated_at` e da tabela de ownership ou da verificacao do veiculo?

**E da tabela `vehicle_current_ownership`**, com `DEFAULT CURRENT_TIMESTAMP`.

### Quando e atualizado

| Cenario                | `updated_at` muda?  |
|------------------------|---------------------|
| Novo registro (claimed)| Sim — via DEFAULT   |
| Transferencia de dono  | Sim — `SET updated_at = CURRENT_TIMESTAMP` no UPDATE |
| Verificacao periodica (`VehicleVerificationService`) | **Nao** — so altera `status` (para 2=Desaparecido) |

### Conclusao

`updated_at` = ultima vez que o **ownership mudou**, **nao** a ultima verificacao de existencia do veiculo.

### Recomendacao

Semanticamente, o campo deveria se chamar `ownership_changed_at` para evitar ambiguidade. Enquanto nao renomearmos, documentar no frontend que `updated_at` reflete a ultima mudanca de propriedade.

---

## 4) Quais statuses recebem `location = null`?

**Qualquer status pode ter `location = null`.** A condicao e sobre os dados, nao sobre o status.

```python
if v.get("location_x") is not None:
    v["location"] = { "x": ..., "y": ..., "z": ... }
else:
    v["location"] = None
```

### Quando `location` e `null`

- Quando o log de ownership **nao continha coordenadas** (ex: logs antigos, registros migrados, edge cases do parser).
- Na pratica, a maioria dos registros recentes tera localizacao preenchida.

### Recomendacao

O client deve tratar `location` como **nullable independentemente do status**. Exemplo de fallback na UI: "Localizacao desconhecida".

---

## 5) CORS/HTTPS: qual e o plano oficial para producao?

### CORS atual (dev)

```python
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            ]
        }
    },
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Server-Hash"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
```

Hoje aceita apenas `localhost:8000` / `127.0.0.1:8000`.

### Para producao

- O SSM roda **na maquina do servidor de jogo** (nao e cloud). Cada server owner roda sua propria instancia.
- O Player App (Gestao) chamara o SSM **diretamente do browser do jogador** via `backend_base_url` que o Gestao fornece por servidor.
- Sera necessario **adicionar a origin do Gestao de producao** (ex: `https://gestao.seudominio.com`) na lista de origins CORS.
- A origin pode ser configuravel via `config.json` para que cada server owner defina a sua (campo `public.player_app_origins`).

### HTTPS

O SSM roda **HTTP** (Flask/Werkzeug puro). Para HTTPS em producao:

| Opcao                | Descricao                                                    |
|----------------------|--------------------------------------------------------------|
| Reverse proxy        | Nginx ou Caddy na frente do SSM com certificado SSL          |
| Cloudflare Tunnel    | `cloudflared` — ja usado no ecossistema Gestao               |

### Recomendacao para o frontend

- Estar preparado para **ambos os schemes** (`http://` e `https://`).
- O `backend_base_url` retornado pelo Gestao para cada servidor define o scheme.
- Nao assumir HTTPS — servidores em dev/LAN podem usar HTTP.

---

## Resumo de campos da resposta de veiculos

| Campo                   | Tipo      | Nullable | Descricao                                     |
|-------------------------|-----------|----------|-----------------------------------------------|
| `entity_id`             | int       | Nao      | ID do container (detalhe interno)              |
| `vehicle_entity_id`     | int       | Sim*     | ID do veiculo (usar como identificador)        |
| `steam_id`              | string    | Nao      | Steam ID do dono                               |
| `player_name`           | string    | Nao      | Nome do jogador dono                           |
| `vehicle_class`         | string    | Sim      | Classe interna (ex: `BPC_Wolfswagen`)          |
| `vehicle_class_display` | string    | Nao      | Nome amigavel (ex: `Wolfswagen`)               |
| `vehicle_asset_id`      | string    | Sim      | Asset ID do veiculo                            |
| `is_vehicle_functional` | int       | Sim      | 1=funcional, 0=nao funcional                   |
| `status`                | int       | Nao      | 0=Ativo, 1=Inativo, 2=Desaparecido, 3=Destruido |
| `status_text`           | string    | Nao      | Label pt-BR (usar `status` int no client)      |
| `location`              | object    | **Sim**  | `{x, y, z}` ou `null`                         |
| `last_ownership_change` | datetime  | Nao      | Quando o dono atual adquiriu o veiculo         |
| `container_class`       | string    | Sim      | Classe do container (detalhe interno)          |
| `updated_at`            | datetime  | Sim      | Ultima mudanca de ownership (nao verificacao)  |

*`vehicle_entity_id` pode ser `null` em edge cases onde o mapeamento container→veiculo falhou.

---

## Contato

Duvidas adicionais sobre o contrato de veiculos: abrir issue ou contatar o dev do SSM.
