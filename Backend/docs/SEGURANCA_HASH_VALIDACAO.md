# 🔒 Segurança: Geração e Validação de Hash

## ❓ Pergunta Importante

**O hash deve ser armazenado ou gerado sempre antes de consultar o servidor?**

## ✅ Resposta: SEMPRE GERAR ANTES DE CONSULTAR

### Por quê?

1. **Segurança Máxima**
   - Hash armazenado pode ser modificado/falsificado
   - Hash gerado na hora = hardware real atual
   - Impossível bypassar sem modificar hardware

2. **Detecção Imediata de Mudanças**
   - Se hardware mudou, hash muda imediatamente
   - Servidor detecta na hora
   - Não depende de cache/armazenamento

3. **Impossível Falsificar**
   - Mesmo que alguém modifique arquivo de hash
   - Servidor sempre recebe hash do hardware atual
   - Validação sempre correta

---

## 🔄 Fluxo Correto de Validação

### A cada 4 horas:

```
Timer dispara (4h desde última validação)
   ↓
1. SSM GERA hash do hardware ATUAL (não usa armazenado!)
   - Coleta MACs, CPU, discos, etc. AGORA
   - Gera hash SHA-256
   ↓
2. SSM COMPARA com hash armazenado (apenas para detecção local)
   - Se diferente: hardware mudou → bloquear localmente
   - Se igual: continuar
   ↓
3. SSM ENVIA hash GERADO (não armazenado!) ao servidor
   POST /api/v1/validate
   {
     "license_key": "SSM-XXXX-XXXX-XXXX",
     "hardware_fingerprint": "hash_gerado_agora",  // ← SEMPRE GERADO NA HORA
     "timestamp": "2025-01-15T10:00:00Z"
   }
   ↓
4. Servidor valida:
   - Hash corresponde ao cadastrado?
   - Licença válida?
   - Não expirada?
   ↓
5. Servidor retorna:
   - Se válido: { "valid": true, "expires_at": "..." }
   - Se inválido: { "valid": false, "reason": "hardware_mismatch" }
   ↓
6. SSM processa resposta:
   - Se válido: continua funcionando, salva resultado
   - Se inválido: BLOQUEIA tudo, mostra tela de revalidação
   ↓
7. SSM ATUALIZA hash armazenado (apenas para comparação futura)
   - Salva hash gerado como "último hash conhecido"
   - Usa para comparação na próxima validação
```

---

## 💾 Uso do Hash Armazenado

### O hash armazenado serve APENAS para:

1. **Detecção Local Rápida**
   - Comparar antes de consultar servidor
   - Se diferente, já bloquear localmente (não precisa esperar servidor)
   - Melhor UX (resposta imediata)

2. **Histórico/Logs**
   - Saber qual era o hash anterior
   - Rastrear mudanças de hardware
   - Debugging

3. **Otimização**
   - Se hash não mudou, pode pular algumas verificações
   - Mas SEMPRE gerar novo para enviar ao servidor

### O hash armazenado NUNCA serve para:

- ❌ Enviar ao servidor (sempre gerar novo)
- ❌ Validação final (servidor decide)
- ❌ Bypass de segurança (impossível)

---

## 🛡️ Estratégia de Segurança em Camadas

### Camada 1: Detecção Local (Rápida)

```python
# Comparar hash atual vs armazenado
current_hash = hardware_fingerprint.generate()  # Gerar AGORA
stored_hash = load_stored_hash()

if current_hash != stored_hash:
    # Hardware mudou - bloquear localmente
    block_functionality()
    show_revalidation_screen()
    return
```

**Vantagem:** Resposta imediata, melhor UX

### Camada 2: Validação no Servidor (Definitiva)

```python
# SEMPRE gerar hash novo para enviar ao servidor
current_hash = hardware_fingerprint.generate()  # Gerar AGORA (não usar armazenado!)

response = license_client.validate(
    license_key=license_key,
    hardware_fingerprint=current_hash  # ← Hash gerado agora
)

if not response['valid']:
    # Servidor bloqueou - hardware não corresponde
    block_functionality()
    show_revalidation_screen()
    return
```

**Vantagem:** Impossível falsificar, servidor tem controle total

---

## 📊 Comparação: Armazenado vs Gerado

| Aspecto | Hash Armazenado | Hash Gerado na Hora |
|---------|----------------|---------------------|
| **Segurança** | ❌ Pode ser falsificado | ✅ Impossível falsificar |
| **Detecção de Mudanças** | ⚠️ Depende de comparação | ✅ Imediata |
| **Performance** | ✅ Rápido | ⚠️ Um pouco mais lento (negligível) |
| **Confiabilidade** | ❌ Pode estar desatualizado | ✅ Sempre atual |
| **Bypass** | ⚠️ Possível modificar arquivo | ✅ Impossível |

**Conclusão:** Sempre gerar na hora para enviar ao servidor!

---

## 🔧 Implementação Recomendada

### Método de Validação

```python
class LicenseValidator:
    def validate_license(self):
        # 1. SEMPRE gerar hash do hardware atual
        current_hash = self.hardware_fingerprint.generate()
        
        # 2. Comparar com armazenado (apenas para detecção local)
        stored_hash = self.load_stored_hash()
        if current_hash != stored_hash:
            # Hardware mudou - bloquear localmente
            self._handle_hardware_change(current_hash, stored_hash)
            return False
        
        # 3. Enviar hash GERADO (não armazenado!) ao servidor
        response = self.license_client.validate(
            license_key=self.license_key,
            hardware_fingerprint=current_hash  # ← Hash gerado agora
        )
        
        # 4. Processar resposta do servidor
        if response['valid']:
            # Servidor validou - atualizar hash armazenado
            self.save_hash(current_hash)  # Salvar para próxima comparação
            return True
        else:
            # Servidor bloqueou
            self._handle_invalid(response)
            return False
```

### Método de Geração (Sempre na Hora)

```python
class HardwareFingerprint:
    def generate(self) -> str:
        """
        SEMPRE gera hash do hardware atual.
        NUNCA retorna hash armazenado.
        """
        # Coletar hardware AGORA
        components = self._collect_all_components()
        
        # Gerar hash
        hash_value = self._generate_hash(components)
        
        return hash_value  # Sempre novo, sempre atual
```

---

## 🎯 Resumo da Estratégia

### ✅ Fazer:

1. **Sempre gerar hash antes de consultar servidor**
   - Coletar hardware atual
   - Gerar hash na hora
   - Enviar ao servidor

2. **Usar hash armazenado apenas para comparação local**
   - Detectar mudanças rapidamente
   - Melhorar UX (resposta imediata)
   - Histórico/logs

3. **Servidor sempre recebe hash gerado na hora**
   - Impossível falsificar
   - Sempre valida hardware atual
   - Controle total no servidor

### ❌ NÃO fazer:

1. **Nunca enviar hash armazenado ao servidor**
   - Pode estar desatualizado
   - Pode ser falsificado
   - Não representa hardware atual

2. **Nunca confiar apenas em hash armazenado**
   - Sempre validar no servidor
   - Hash armazenado é apenas para comparação local

---

## 🔐 Segurança Máxima

### Fluxo Completo (Seguro):

```
1. Gerar hash atual → hardware real
2. Comparar com armazenado → detecção local rápida
3. Enviar hash atual ao servidor → validação definitiva
4. Servidor decide → bloqueia ou libera
5. Atualizar hash armazenado → para próxima comparação
```

**Resultado:** 
- ✅ Impossível falsificar (servidor sempre recebe hash atual)
- ✅ Detecção rápida (comparação local)
- ✅ Validação definitiva (servidor decide)
- ✅ Sempre atualizado (hash sempre gerado na hora)

---

## 📝 Conclusão

**SEMPRE gerar o hash antes de consultar o servidor!**

O hash armazenado serve apenas para:
- Detecção local rápida de mudanças
- Histórico e logs
- Comparação (não para envio)

O servidor sempre recebe o hash gerado na hora, garantindo:
- Hardware atual validado
- Impossível falsificar
- Segurança máxima

