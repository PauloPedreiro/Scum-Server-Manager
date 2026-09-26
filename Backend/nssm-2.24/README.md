# NSSM - Non-Sucking Service Manager

## 📋 **Descrição**

Este diretório contém o **NSSM (Non-Sucking Service Manager)** versão 2.24, copiado para dentro do projeto para garantir portabilidade e independência de instalação externa.

## 📁 **Estrutura**

```
nssm-2.24/
├── win64/
│   └── nssm.exe          # Executável NSSM 64-bit
└── README.md             # Este arquivo
```

## 🔧 **Uso**

### **Comandos Básicos:**
```cmd
# Verificar status do serviço
nssm-2.24\win64\nssm.exe status SCUMServer

# Parar serviço
nssm-2.24\win64\nssm.exe stop SCUMServer

# Iniciar serviço
nssm-2.24\win64\nssm.exe start SCUMServer

# Editar configuração do serviço
nssm-2.24\win64\nssm.exe edit SCUMServer
```

### **Nos Scripts:**
Os scripts do projeto (`start-server.bat`, `stop-server.bat`, `restart-server.ps1`) usam caminhos relativos para acessar o NSSM:

```batch
set NSSMPath=%~dp0..\..\..\nssm-2.24\win64\nssm.exe
```

## ⚠️ **Importante**

- **Privilégios**: O NSSM requer privilégios de administrador para controlar serviços
- **Portabilidade**: Este NSSM é específico para Windows 64-bit
- **Versão**: NSSM v2.24 (31/08/2014)

## 🔗 **Referências**

- **Site Oficial**: https://nssm.cc/
- **Documentação**: https://nssm.cc/usage
- **Download**: https://nssm.cc/download

## 📝 **Notas**

- O NSSM foi copiado de `C:\nssm-2.24\win64\nssm.exe` para garantir que o projeto seja independente
- Todos os scripts foram atualizados para usar o caminho relativo
- A documentação foi atualizada para refletir a nova localização
