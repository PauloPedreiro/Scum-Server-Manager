# Endpoint: /api/players/painelplayers

## Método
GET

## Descrição
Processa o log mais recente de login/logout do servidor SCUM, atualiza o banco de dados de jogadores, gera tags de tempo de jogo, atualiza o status online/offline e envia (se necessário) um webhook para o Discord com o status dos jogadores online.

## Funcionamento
- Lê o arquivo de log mais recente do SCUM (UTF-16LE).
- Extrai informações de login/logout dos jogadores.
- Atualiza o banco de dados JSON (`players.json`), somando tempo de jogo e marcando status online/offline.
- O **tempo de jogo** é calculado com base na diferença real entre o horário de login e logout extraído do log (não da hora do processamento), somando ao total acumulado do jogador.
- Exemplo: se o jogador logou às 14:49 e saiu às 16:00, serão somados 1h11min ao total.
- Após restart do servidor (novo log), todos os jogadores que não aparecem no novo log de login são marcados como offline.
- Gera tags de ranking por tempo de jogo (com emojis).
- Só envia o webhook para o Discord se houver mudança na lista de jogadores online (alguém entrou ou saiu).
- Salva o último estado de online em `lastOnline.json` para comparação futura.

## Parâmetros
Nenhum parâmetro necessário.

## Resposta
- **success**: booleano indicando sucesso da operação
- **message**: mensagem de status
- **data**: array com os dados dos jogadores

### Exemplo de resposta
```json
{
  "success": true,
  "message": "Dados processados com sucesso",
  "data": [
    {
      "playerName": "ze",
      "steamId": "76561199680509725",
      "totalPlayTime": 10624000,
      "lastLogin": "2025-07-12T16:51:22.000Z",
      "lastLogout": "2025-07-12T16:51:15.000Z",
      "isOnline": true,
      "tags": ["Iniciante", "Online"]
    },
    ...
  ]
}
```

## Lógica de envio do Webhook
- O webhook só é enviado se a lista de jogadores online mudou desde a última atualização.
- O status enviado para o Discord mostra:
  - Estatísticas gerais
  - Lista de jogadores online, cada um com emoji de ranking, nome e tempo de jogo (ex: 🥉   ze - 10h)
  - Última atualização
- Emojis de ranking:
  - 🆕 Iniciante: menos de 5h
  - 🥉 Novato: 5h a 19h
  - 🥈 Regular: 20h a 49h
  - 🥇 Experiente: 50h a 99h
  - 🏆 Veterano: 100h a 199h
  - 👑 Lendário: 200h ou mais

## Observações
- O endpoint é seguro para ser chamado periodicamente (ex: via cron), pois só envia webhook se houver mudança real.
- O banco de dados e o status online são sempre atualizados conforme o log mais recente.
- Após restart do servidor, apenas jogadores que realmente logaram novamente aparecem como online.
- O tempo de jogo é acumulado corretamente, sessão por sessão, com base nas datas reais do log. 