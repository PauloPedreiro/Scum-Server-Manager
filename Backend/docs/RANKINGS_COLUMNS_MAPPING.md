# 🗺️ Mapeamento de Colunas para Rankings

## ✅ Colunas Confirmadas em `survival_stats_snapshot`

Após consulta ao banco de dados `data/SSM.db`, os nomes exatos das colunas são:

### Rankings do `survival_stats_snapshot`

| # | Ranking | Coluna | Tipo | Descrição |
|---|---------|--------|------|-----------|
| 5 | Maior Cagão | `total_defecations` | INTEGER | Total de defecações |
| 7 | Caça | `animals_killed` | INTEGER | Total de animais mortos |
| 8 | Master Bruce Lee | `players_knocked_out` | INTEGER | Total de nocautes em jogadores ✅ |
| 9 | Headshots | `headshots` | INTEGER | Total de headshots |
| 10 | Minutos Sobrevividos | `minutes_survived` | REAL | Minutos de sobrevivência |
| 11 | Overdoses | `overdose` | INTEGER | Total de overdoses |
| 12 | Hulk (Maior Peso) | `highest_weight_carried` | REAL | Maior peso já carregado |

### Rankings de outras tabelas

| # | Ranking | Tabela | Query | Descrição |
|---|---------|--------|-------|-----------|
| 1 | Kills | `kill_events` | `COUNT(*) WHERE killer_steam_id = X AND event_type = 'kill' AND killer_is_npc = 0` | Total de kills |
| 1 | Deaths | `kill_events` | `COUNT(*) WHERE victim_steam_id = X AND event_type = 'kill'` | Total de deaths |
| 2 | Longest Shot | `kill_events` | `MAX(distance) WHERE killer_steam_id = X` | Maior distância de tiro |
| 3 | Lockpicking Success | `minigame_events` | `COUNT(*) WHERE steam_id = X AND minigame_type = 'LockpickingMinigame_C' AND success = 1` | Sucessos |
| 3 | Lockpicking Fails | `minigame_events` | `COUNT(*) WHERE steam_id = X AND minigame_type = 'LockpickingMinigame_C' AND success = 0` | Falhas |
| 4 | Suicides | `kill_events` | `COUNT(*) WHERE victim_steam_id = X AND event_type = 'suicide'` | Total de suicídios |
| 6 | Vehicle Destruction | `vehicle_destruction_events` | `COUNT(*) WHERE owner_steam_id = X` | Veículos destruídos |

## 📊 Todas as Colunas Disponíveis

A tabela `survival_stats_snapshot` possui **79 colunas** no total:

### Métricas Principais (75 colunas numéricas)

1. `user_profile_id` - ID do perfil do jogador
2. `highest_positive_fame_points` - Maior pontuação de fama positiva
3. `doors_claimed` - Portas reivindicadas
4. `animals_killed` - Animais mortos ⭐
5. `minutes_survived` - Minutos sobrevividos ⭐
6. `kills` - Kills
7. `deaths` - Deaths
8. `locks_picked` - Fechaduras abertas
9. `puppets_killed` - Puppets mortos
10. `guns_crafted` - Armas fabricadas
11. `bullets_crafted` - Balas fabricadas
12. `arrows_crafted` - Flechas fabricadas
13. `clothing_crafted` - Roupas fabricadas
14. `longest_kill_distance` - Maior distância de kill
15. `melee_kills` - Mortes corpo a corpo ⭐
16. `archery_kills` - Mortes com arco
17. `players_knocked_out` - Jogadores nocauteados ⭐
18. `total_defecations` - Total de defecações ⭐
19. `total_urinations` - Total de urinações
20. `lights_fired` - Luzes acesas
21. `containers_looted` - Containers saqueados
22. `items_put_into_containers` - Itens colocados em containers
23. `deaths_by_prisoners` - Mortes por prisioneiros
24. `animals_skinned` - Animais esfolados
25. `food_eaten` - Comida consumida
26. `distance_travelled_by_foot` - Distância a pé
27. `wounds_patched` - Feridas tratadas
28. `items_picked_up` - Itens coletados
29. `liquid_drank` - Líquidos bebidos
30. `teeth_lost` - Dentes perdidos
31. `total_calories_intake` - Total de calorias ingeridas
32. `shots_fired` - Tiros disparados
33. `shots_hit` - Tiros que acertaram
34. `headshots` - Headshots ⭐
35. `melee_weapon_swings` - Golpes com arma corpo a corpo
36. `melee_weapon_hits` - Acertos com arma corpo a corpo
37. `melee_weapons_crafted` - Armas corpo a corpo fabricadas
38. `drone_kills` - Drones mortos
39. `sentry_kills` - Sentinelas mortas
40. `prisoner_kills` - Prisioneiros mortos
41. `puppets_knocked_out` - Puppets nocauteados
42. `diarrheas` - Diarreias
43. `vomits` - Vômitos
44. `distance_travelled_in_vehicle` - Distância em veículo
45. `mushrooms_eaten` - Cogumelos comidos
46. `highest_muscle_mass` - Maior massa muscular
47. `highest_fat` - Maior gordura
48. `heart_attacks` - Ataques cardíacos
49. `overdose` - Overdoses ⭐
50. `starvation` - Fomes
51. `highest_damage_taken` - Maior dano recebido
52. `highest_weight_carried` - Maior peso carregado ⭐
53. `lowest_negative_fame_points` - Menor pontuação de fama negativa
54. `distance_travelled_swimming` - Distância nadando
55. `crows_killed` - Corvos mortos
56. `seagulls_killed` - Gaivotas mortas
57. `horses_killed` - Cavalos mortos
58. `boars_killed` - Javalis mortos
59. `bears_killed` - Ursos mortos
60. `goats_killed` - Cabras mortas
61. `deers_killed` - Veados mortos
62. `chickens_killed` - Galinhas mortas
63. `rabbits_killed` - Coelhos mortos
64. `donkeys_killed` - Burros mortos
65. `times_mauled_by_bear` - Vezes atacado por urso
66. `longest_animal_kill_distance` - Maior distância de kill em animal
67. `alcohol_drank` - Álcool bebido
68. `foliage_cut` - Vegetação cortada
69. `distance_travel_by_boat` - Distância em barco
70. `distance_sailed` - Distância navegando
71. `times_caught_by_shark` - Vezes pego por tubarão
72. `times_escaped_shark_bite` - Vezes escapou de mordida de tubarão
73. `wolves_killed` - Lobos mortos
74. `last_fame_point_award_consecutive_days` - Últimos dias consecutivos de premiação de fama
75. `firearm_kills` - Mortes com arma de fogo
76. `bare_handed_kills` - Mortes desarmadas ⭐

### Colunas de Identificação (4 colunas)

77. `steam_id` - Steam ID do jogador
78. `player_name` - Nome do jogador
79. `snapshot_at` - Timestamp do snapshot

## 📌 Notas Importantes

1. ⭐ = Colunas usadas nos rankings solicitados
2. Para rankings que usam `MAX()`, usar sempre o snapshot mais recente (maior `snapshot_at`)
3. Para rankings que usam `COUNT()`, contar todos os registros da tabela relacionada
4. A tabela `survival_stats_snapshot` é atualizada periodicamente (configurável, padrão: 30 minutos)
5. Alguns rankings podem precisar agrupar por `steam_id` e pegar o máximo ou somar valores

## 🔄 Recomendações

### Para Master Bruce Lee:
✅ **Confirmado**: `players_knocked_out` - Total de nocautes em jogadores

Esta coluna foi confirmada como a correta para o ranking "Master Bruce Lee", representando jogadores com mais nocautes (knockouts).

### Para Caça:
- Usar `animals_killed` - Total geral
- Ou criar ranking específico por tipo de animal (ex: `boars_killed`, `deers_killed`, `wolves_killed`)

**Recomendação**: Usar `animals_killed` como principal.

