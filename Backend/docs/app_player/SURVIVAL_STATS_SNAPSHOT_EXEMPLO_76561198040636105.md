# Player App - Survival Stats Snapshot (Exemplo real)

Este documento contém um exemplo real de retorno baseado na tabela `survival_stats_snapshot` do `SSM.db`, para validação do dev do Gestão.

---

## 1) Identificação

- Endpoint de referência (admin/painel): `GET /api/survival/player/<identifier>`
- Endpoint de referência (Player App): `GET /api/player/survival-stats/snapshot`
- `steam_id`: `76561198040636105`
- `player_name`: `Pedreiro`
- `user_profile_id`: `1`
- `snapshot_at`: `2026-02-18T03:18:49.695751`

---

## 2) Resumo (campos mais relevantes)

- `minutes_survived`: `2138.903076171875`
- `distance_travelled_by_foot`: `7837.12060546875`
- `distance_travelled_in_vehicle`: `465.83282470703125`
- `items_picked_up`: `2919`
- `containers_looted`: `6`
- `total_calories_intake`: `5147`
- `food_eaten`: `5.399999618530273`
- `liquid_drank`: `1.0`
- `total_urinations`: `4`
- `highest_weight_carried`: `76.61650848388672`
- `highest_positive_fame_points`: `45.590370178222656`

Derivados (se aplicável):

- `kdr`: `0`
- `accuracy_percent`: `null`

---

## 3) JSON completo (linha da tabela)

```json
{
  "steam_id": "76561198040636105",
  "player_name": "Pedreiro",
  "snapshot_at": "2026-02-18T03:18:49.695751",
  "user_profile_id": 1,
  "highest_positive_fame_points": 45.590370178222656,
  "doors_claimed": 0,
  "animals_killed": 0,
  "minutes_survived": 2138.903076171875,
  "kills": 0,
  "deaths": 0,
  "locks_picked": 0,
  "puppets_killed": 0,
  "guns_crafted": 0,
  "bullets_crafted": 0,
  "arrows_crafted": 0,
  "clothing_crafted": 0,
  "longest_kill_distance": 0.0,
  "melee_kills": 0,
  "archery_kills": 0,
  "players_knocked_out": 0,
  "total_defecations": 0,
  "total_urinations": 4,
  "lights_fired": 0,
  "containers_looted": 6,
  "items_put_into_containers": 0,
  "deaths_by_prisoners": 0,
  "animals_skinned": 0,
  "food_eaten": 5.399999618530273,
  "distance_travelled_by_foot": 7837.12060546875,
  "wounds_patched": 0,
  "items_picked_up": 2919,
  "liquid_drank": 1.0,
  "teeth_lost": 0,
  "total_calories_intake": 5147,
  "shots_fired": 0,
  "shots_hit": 0,
  "headshots": 0,
  "melee_weapon_swings": 0,
  "melee_weapon_hits": 0,
  "melee_weapons_crafted": 0,
  "drone_kills": 0,
  "sentry_kills": 0,
  "prisoner_kills": 0,
  "puppets_knocked_out": 0,
  "diarrheas": 0,
  "vomits": 0,
  "distance_travelled_in_vehicle": 465.83282470703125,
  "mushrooms_eaten": 0,
  "highest_muscle_mass": 67.49374389648438,
  "highest_fat": 20.824134826660156,
  "heart_attacks": 0,
  "overdose": 0,
  "starvation": 0,
  "highest_damage_taken": 0.0,
  "highest_weight_carried": 76.61650848388672,
  "lowest_negative_fame_points": 0.0,
  "distance_travelled_swimming": 0.0,
  "crows_killed": 0,
  "seagulls_killed": 0,
  "horses_killed": 0,
  "boars_killed": 0,
  "bears_killed": 0,
  "goats_killed": 0,
  "deers_killed": 0,
  "chickens_killed": 0,
  "rabbits_killed": 0,
  "donkeys_killed": 0,
  "times_mauled_by_bear": 0,
  "longest_animal_kill_distance": 0.0,
  "alcohol_drank": 0,
  "foliage_cut": 0,
  "distance_travel_by_boat": 0.0,
  "distance_sailed": 0.0,
  "times_caught_by_shark": 0,
  "times_escaped_shark_bite": 0,
  "wolves_killed": 0,
  "last_fame_point_award_consecutive_days": 0,
  "firearm_kills": 0,
  "bare_handed_kills": 0
}
```
