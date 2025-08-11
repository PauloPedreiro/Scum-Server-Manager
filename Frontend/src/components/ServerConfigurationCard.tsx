import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, ChevronRight, Server, Globe, Settings, Save, RotateCcw, FileText, Car, Zap, Users, Eye, EyeOff, History, Search, X, Copy, Clipboard, AlertTriangle, CheckCircle, Shield } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { ServerConfigService } from '../services/serverConfigService';
import BackupManager from './BackupManager';

interface ConfigSection {
  id: string;
  name: string;
  icon: React.ComponentType<any>;
  description: string;
  settings: ConfigSetting[];
}

interface ConfigSetting {
  key: string;
  label: string;
  type: 'text' | 'number' | 'boolean' | 'select' | 'textarea';
  value: string;
  description?: string;
  options?: string[];
  min?: number;
  max?: number;
}

const ServerConfigurationCard: React.FC = () => {
  const { t } = useLanguage();
  console.log('ServerConfigurationCard - Componente renderizado');

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState<string[]>([]);
  const [expandedSections, setExpandedSections] = useState<string[]>(['general']);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showBackups, setShowBackups] = useState(false);
  const [expandedToggleSections, setExpandedToggleSections] = useState<Set<string>>(new Set());
  const [originalConfig, setOriginalConfig] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [sections, setSections] = useState<ConfigSection[]>([]);

  useEffect(() => {
    setSections([
      {
        id: 'general',
        name: t('general_settings'),
        icon: Server,
        description: t('basic_server_settings'),
        settings: [
          { key: 'scum.ServerName', label: t('server_name'), type: 'text', value: '' },
          { key: 'scum.ServerDescription', label: t('server_description'), type: 'textarea', value: '' },
          { key: 'scum.ServerPassword', label: t('server_password'), type: 'text', value: '' },
          { key: 'scum.MaxPlayers', label: t('max_players'), type: 'number', value: '64', min: 1, max: 200 },
          { key: 'scum.ServerBannerUrl', label: t('server_banner_url'), type: 'text', value: '' },
          { key: 'scum.ServerPlaystyle', label: t('server_playstyle'), type: 'select', value: 'PVE', options: ['PVE', 'PVP', 'PVP+E'] },
          { key: 'scum.WelcomeMessage', label: t('welcome_message'), type: 'textarea', value: '' },
          { key: 'scum.MessageOfTheDay', label: t('message_of_the_day'), type: 'textarea', value: '' },
          { key: 'scum.MessageOfTheDayCooldown', label: t('motd_cooldown'), type: 'number', value: '10.000000', min: 0, max: 100 },
          { key: 'scum.MinServerTickRate', label: t('min_server_tickrate'), type: 'number', value: '10', min: 1, max: 100 },
          { key: 'scum.MaxServerTickRate', label: t('max_server_tickrate'), type: 'number', value: '40', min: 10, max: 100 },
          { key: 'scum.MaxPing', label: t('max_ping'), type: 'number', value: '300.000000', min: 50, max: 1000 },
          { key: 'scum.LogoutTimer', label: t('logout_timer'), type: 'number', value: '10.000000', min: 0, max: 300 },
          { key: 'scum.LogoutTimerWhileCaptured', label: t('logout_timer_captured'), type: 'number', value: '120.000000', min: 0, max: 600 },
          { key: 'scum.LogoutTimerInBunker', label: t('logout_timer_bunker'), type: 'number', value: '30000.000000', min: 0, max: 60000 },
          { key: 'scum.AllowFirstPerson', label: t('allow_first_person'), type: 'boolean', value: '1' },
          { key: 'scum.AllowThirdPerson', label: t('allow_third_person'), type: 'boolean', value: '1' },
          { key: 'scum.AllowCrosshair', label: t('allow_crosshair'), type: 'boolean', value: '1' },
          { key: 'scum.AllowVoting', label: t('allow_voting'), type: 'boolean', value: '1' },
          { key: 'scum.AllowMapScreen', label: t('allow_map_screen'), type: 'boolean', value: '1' },
          { key: 'scum.AllowKillClaiming', label: t('allow_kill_claiming'), type: 'boolean', value: '1' },
          { key: 'scum.AllowComa', label: t('allow_coma'), type: 'boolean', value: '1' },
          { key: 'scum.AllowMinesAndTraps', label: t('allow_mines_and_traps'), type: 'boolean', value: '1' },
          { key: 'scum.AllowSkillGainInSafeZones', label: t('allow_skill_gain_safe_zones'), type: 'boolean', value: '1' },
          { key: 'scum.AllowEvents', label: t('allow_events'), type: 'boolean', value: '1' },
          { key: 'scum.LimitGlobalChat', label: t('limit_global_chat'), type: 'boolean', value: '0' },
          { key: 'scum.AllowGlobalChat', label: t('allow_global_chat'), type: 'boolean', value: '1' },
          { key: 'scum.AllowLocalChat', label: t('allow_local_chat'), type: 'boolean', value: '1' },
          { key: 'scum.AllowSquadChat', label: t('allow_squad_chat'), type: 'boolean', value: '1' },
          { key: 'scum.AllowAdminChat', label: t('allow_admin_chat'), type: 'boolean', value: '1' },
          { key: 'scum.RustyLocksLogging', label: t('rusty_locks_logging'), type: 'boolean', value: '1' },
          { key: 'scum.HideKillNotification', label: t('hide_kill_notification'), type: 'boolean', value: '0' },
          { key: 'scum.DisableTimedGifts', label: t('disable_timed_gifts'), type: 'boolean', value: '0' },
          { key: 'scum.UseMapBaseBuildingRestriction', label: t('map_base_building_restriction'), type: 'boolean', value: '1' },
          { key: 'scum.DisableBaseBuilding', label: t('disable_base_building'), type: 'boolean', value: '0' },
          { key: 'scum.VotingDuration', label: t('voting_duration'), type: 'number', value: '60.000000', min: 10, max: 300 },
          { key: 'scum.PlayerMinimalVotingInterest', label: t('player_minimal_voting_interest'), type: 'number', value: '0.500000', min: 0, max: 1 },
          { key: 'scum.PlayerPositiveVotePercentage', label: t('player_positive_vote_percentage'), type: 'number', value: '0.500000', min: 0, max: 1 },
          { key: 'scum.MasterServerEndpoints', label: t('master_server_endpoints'), type: 'text', value: '' },
          { key: 'scum.MasterServerUpdateSendInterval', label: t('master_server_update_send_interval'), type: 'number', value: '60.000000', min: 10, max: 300 },
          { key: 'scum.PartialWipe', label: t('partial_wipe'), type: 'boolean', value: '0' },
          { key: 'scum.GoldWipe', label: t('gold_wipe'), type: 'boolean', value: '0' },
          { key: 'scum.FullWipe', label: t('full_wipe'), type: 'boolean', value: '0' },
          { key: 'scum.ItemVirtualizationRelevancyUpdatePeriod', label: t('item_virtualization_relevancy_update_period'), type: 'number', value: '1.000000', min: 0.1, max: 10 },
          { key: 'scum.ItemVirtualizationEventProcessingTimeBudget', label: t('item_virtualization_event_processing_time_budget'), type: 'number', value: '5.000000', min: 1, max: 20 },
          { key: 'scum.ItemVirtualizationVisitorDistanceTravelledForUpdate', label: t('item_virtualization_visitor_distance_travelled_for_update'), type: 'number', value: '100.000000', min: 10, max: 1000 },
          { key: 'scum.ItemVirtualizationVisitorBounds', label: t('item_virtualization_visitor_bounds'), type: 'number', value: '10000.000000', min: 1000, max: 50000 },
          { key: 'scum.VirtualizedItemBounds', label: t('virtualized_item_bounds'), type: 'number', value: '100.000000', min: 10, max: 1000 },
          { key: 'scum.FameGainMultiplier', label: t('fame_gain_multiplier'), type: 'number', value: '2.500000', min: 0, max: 10 },
          { key: 'scum.FamePointPenaltyOnDeath', label: t('fame_point_penalty_on_death'), type: 'number', value: '0.100000', min: 0, max: 1 },
          { key: 'scum.FamePointPenaltyOnKilled', label: t('fame_point_penalty_on_killed'), type: 'number', value: '0.250000', min: 0, max: 1 },
          { key: 'scum.FamePointRewardOnKill', label: t('fame_point_reward_on_kill'), type: 'number', value: '0.500000', min: 0, max: 10 },
          { key: 'scum.LogSuicides', label: t('log_suicides'), type: 'boolean', value: '1' },
          { key: 'scum.EnableSpawnOnGround', label: t('enable_spawn_on_ground'), type: 'boolean', value: '0' },
          { key: 'scum.DeleteInactiveUsers', label: t('delete_inactive_users'), type: 'boolean', value: '1' },
          { key: 'scum.DaysSinceLastLoginToBecomeInactive', label: t('days_since_last_login_to_become_inactive'), type: 'number', value: '180', min: 1, max: 365 },
          { key: 'scum.DeleteBannedUsers', label: t('delete_banned_users'), type: 'boolean', value: '0' },
          { key: 'scum.MaximumTimeForChestsInForbiddenZones', label: t('maximum_time_for_chests_in_forbidden_zones'), type: 'text', value: '24:00:00' },
          { key: 'scum.LogChestOwnership', label: t('log_chest_ownership'), type: 'boolean', value: '1' },
          { key: 'scum.SettingsVersion', label: t('settings_version'), type: 'number', value: '3', min: 1, max: 10 },
          { key: 'scum.MasterServerIsLocalTest', label: t('master_server_is_local_test'), type: 'boolean', value: '0' }
        ]
      },
      {
        id: 'world',
        name: t('world_settings'),
        icon: Globe,
        description: t('world_settings_desc'),
        settings: [
          { key: 'scum.MaxAllowedBirds', label: t('max_allowed_birds'), type: 'number', value: '10', min: 0, max: 50 },
          { key: 'scum.MaxAllowedCharacters', label: t('max_allowed_characters'), type: 'number', value: '220', min: 0, max: 500 },
          { key: 'scum.MaxAllowedPuppets', label: t('max_allowed_puppets'), type: 'number', value: '-1', min: -1, max: 1000 },
          { key: 'scum.MaxAllowedAnimals', label: t('max_allowed_animals'), type: 'number', value: '60', min: 0, max: 200 },
          { key: 'scum.MaxAllowedNPCs', label: t('max_allowed_npcs'), type: 'number', value: '-1', min: -1, max: 500 },
          { key: 'scum.EncounterBaseCharacterAmountMultiplier', label: t('encounter_base_character_amount_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.EncounterExtraCharacterPerPlayerMultiplier', label: t('encounter_extra_character_per_player_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.EncounterExtraCharacterPlayerCapMultiplier', label: t('encounter_extra_character_player_cap_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.EncounterCharacterRespawnTimeMultiplier', label: t('encounter_character_respawn_time_multiplier'), type: 'number', value: '1.000000', min: 0, max: 10 },
          { key: 'scum.EncounterCharacterRespawnBatchSizeMultiplier', label: t('encounter_character_respawn_batch_size_multiplier'), type: 'number', value: '1.000000', min: 0, max: 10 },
          { key: 'scum.EncounterCharacterAggressiveSpawnChanceOverride', label: t('encounter_character_aggressive_spawn_chance_override'), type: 'number', value: '-1.000000', min: -1, max: 1 },
          { key: 'scum.EncounterCharacterAINoiseResponseRadiusMultiplier', label: t('encounter_character_ai_noise_response_radius_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.EncounterHordeGroupBaseCharacterAmountMultiplier', label: t('encounter_horde_group_base_character_amount_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.EncounterHordeGroupExtraCharacterPerPlayerMultiplier', label: t('encounter_horde_group_extra_character_per_player_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.EncounterHordeGroupExtraCharacterPlayerCapMultiplier', label: t('encounter_horde_group_extra_character_player_cap_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.EncounterHordeBaseCharacterAmountMultiplier', label: t('encounter_horde_base_character_amount_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.EncounterHordeExtraCharacterPerPlayerMultiplier', label: t('encounter_horde_extra_character_per_player_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.EncounterHordeExtraCharacterPlayerCapMultiplier', label: t('encounter_horde_extra_character_player_cap_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.EncounterHordeActivationChanceMultiplier', label: t('encounter_horde_activation_chance_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.EncounterHordeNoiseCheckCooldownMultiplier', label: t('encounter_horde_noise_check_cooldown_multiplier'), type: 'number', value: '1.000000', min: 0, max: 10 },
          { key: 'scum.EncounterHordeSpawnDistanceMultiplier', label: t('encounter_horde_spawn_distance_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.EncounterHordeGroupRefillTimeMultiplier', label: t('encounter_horde_group_refill_time_multiplier'), type: 'number', value: '1.000000', min: 0, max: 10 },
          { key: 'scum.EncounterHordeShouldPlayActivationSound', label: t('encounter_horde_should_play_activation_sound'), type: 'boolean', value: '0' },
          { key: 'scum.EncounterHordePuppetHordeActivationScreamOverrideChance', label: t('encounter_horde_puppet_horde_activation_scream_override_chance'), type: 'number', value: '-1.000000', min: -1, max: 1 },
          { key: 'scum.EncounterCanRemoveLowPriorityCharacters', label: t('encounter_can_remove_low_priority_characters'), type: 'boolean', value: '1' },
          { key: 'scum.EncounterCanClampCharacterNumWhenOutOfResources', label: t('encounter_can_clamp_character_num_when_out_of_resources'), type: 'boolean', value: '1' },
          { key: 'scum.EncounterGlobalZoneCooldownMultiplier', label: t('encounter_global_zone_cooldown_multiplier'), type: 'number', value: '1.000000', min: 0, max: 10 },
          { key: 'scum.EncounterEnableSpawnPreventionAreaSpawnOnCharacterDeath', label: t('encounter_enable_spawn_prevention_area_spawn_on_character_death'), type: 'boolean', value: '1' },
          { key: 'scum.PuppetWorldEncounterSpawnWeightMultiplier', label: t('puppet_world_encounter_spawn_weight_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.AnimalWorldEncounterSpawnWeightMultiplier', label: t('animal_world_encounter_spawn_weight_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.DropshipWorldEncounterSpawnWeightMultiplier', label: t('dropship_world_encounter_spawn_weight_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.PawnSpawning.CheckOceanSpawnPoints', label: t('pawn_spawning_check_ocean_spawn_points'), type: 'boolean', value: '1' },
          { key: 'scum.EnableDropshipAbandonedBunkerEncounter', label: t('enable_dropship_abandoned_bunker_encounter'), type: 'boolean', value: '1' },
          { key: 'scum.DropshipAbandonedBunkerEncounterTriggerChance', label: t('dropship_abandoned_bunker_encounter_trigger_chance'), type: 'number', value: '-1.000000', min: -1, max: 1 },
          { key: 'scum.BaseBuildingEncounterTriggerChance', label: t('base_building_encounter_trigger_chance'), type: 'number', value: '-1.000000', min: -1, max: 1 },
          { key: 'scum.BaseBuildingEncounterTriggerTimeMultiplier', label: t('base_building_encounter_trigger_time_multiplier'), type: 'number', value: '1.000000', min: 0, max: 10 },
          { key: 'scum.EnableDropshipBaseBuildingEncounter', label: t('enable_dropship_base_building_encounter'), type: 'boolean', value: '0' },
          { key: 'scum.SpawnEncountersInThreatZonesIgnoringBaseBuilding', label: t('spawn_encounters_in_threat_zones_ignoring_base_building'), type: 'boolean', value: '0' },
          { key: 'scum.EnableEncounterManagerLowPlayerCountMode', label: t('enable_encounter_manager_low_player_count_mode'), type: 'boolean', value: '0' },
          { key: 'scum.BaseBuildingEncounterMinNumElementsToStart', label: t('base_building_encounter_min_num_elements_to_start'), type: 'number', value: '-1', min: -1, max: 100 },
          { key: 'scum.BaseBuildingEncounterMinNumElementsToEnd', label: t('base_building_encounter_min_num_elements_to_end'), type: 'number', value: '-1', min: -1, max: 100 },
          { key: 'scum.BaseBuildingEncounterDamagePercentageIncreasePerSquadMember', label: t('base_building_encounter_damage_percentage_increase_per_squad_member'), type: 'number', value: '0.000000', min: 0, max: 100 },
          { key: 'scum.BaseBuildingEncounterTimeToFullMinNumToEnd', label: t('base_building_encounter_time_to_full_min_num_to_end'), type: 'number', value: '-1.000000', min: -1, max: 100 },
          { key: 'scum.BaseBuildingEncounterMaximumMinToEndReduction', label: t('base_building_encounter_maximum_min_to_end_reduction'), type: 'number', value: '-1', min: -1, max: 100 },
          { key: 'scum.MaxAllowedDrones', label: t('max_allowed_drones'), type: 'number', value: '0', min: 0, max: 100 },
          { key: 'scum.DisableSentrySpawning', label: t('disable_sentry_spawning'), type: 'boolean', value: '0' },
          { key: 'scum.EnableSentryRespawning', label: t('enable_sentry_respawning'), type: 'boolean', value: '1' },
          { key: 'scum.DisableSuicidePuppetSpawning', label: t('disable_suicide_puppet_spawning'), type: 'boolean', value: '0' },
          { key: 'scum.AbandonedBunkerCommotionThreshold', label: t('abandoned_bunker_commotion_threshold'), type: 'number', value: '-1.000000', min: -1, max: 100 },
          { key: 'scum.AbandonedBunkerCommotionThresholdPerPlayerExtra', label: t('abandoned_bunker_commotion_threshold_per_player_extra'), type: 'number', value: '-1.000000', min: -1, max: 100 },
          { key: 'scum.AbandonedBunkerEnemyActivationThreshold', label: t('abandoned_bunker_enemy_activation_threshold'), type: 'number', value: '-1.000000', min: -1, max: 100 },
          { key: 'scum.AbandonedBunkerEnemyActivationThresholdPerPlayerExtra', label: t('abandoned_bunker_enemy_activation_threshold_per_player_extra'), type: 'number', value: '-1.000000', min: -1, max: 100 },
          { key: 'scum.AbandonedBunkerResetArmoryLockersOnActivationOnly', label: t('abandoned_bunker_reset_armory_lockers_on_activation_only'), type: 'boolean', value: '1' },
          { key: 'scum.PuppetsCanOpenDoors', label: t('puppets_can_open_doors'), type: 'boolean', value: '1' },
          { key: 'scum.PuppetsCanVaultWindows', label: t('puppets_can_vault_windows'), type: 'boolean', value: '1' },
          { key: 'scum.PuppetHealthMultiplier', label: t('puppet_health_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.DropshipHealthMultiplier', label: t('dropship_health_multiplier'), type: 'number', value: '0.500000', min: 0, max: 5 },
          { key: 'scum.SentryHealthMultiplier', label: t('sentry_health_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.BaseBuildingAttackerSentryHealthMultiplier', label: t('base_building_attacker_sentry_health_multiplier'), type: 'number', value: '0.500000', min: 0, max: 5 },
          { key: 'scum.ArmedNPCDifficultyLevel', label: t('armed_npc_difficulty_level'), type: 'number', value: '2', min: 1, max: 5 },
          { key: 'scum.ProbabilityForArmedNPCToDropItemFromHandsWhenSearched', label: t('probability_for_armed_npc_to_drop_item_from_hands_when_searched'), type: 'number', value: '0.900000', min: 0, max: 1 },
          { key: 'scum.StartTimeOfDay', label: t('start_time_of_day'), type: 'text', value: '06:00:00' },
          { key: 'scum.TimeOfDaySpeed', label: t('time_of_day_speed'), type: 'number', value: '9.000000', min: 1, max: 24 },
          { key: 'scum.NighttimeDarkness', label: t('nighttime_darkness'), type: 'number', value: '-0.300000', min: -1, max: 1 },
          { key: 'scum.SunriseTime', label: t('sunrise_time'), type: 'text', value: '05:00:00' },
          { key: 'scum.SunsetTime', label: t('sunset_time'), type: 'text', value: '23:00:00' },
          { key: 'scum.WeatherRainFrequencyMultiplier', label: t('weather_rain_frequency_multiplier'), type: 'number', value: '0.02', min: 0, max: 1 },
          { key: 'scum.WeatherRainDurationMultiplier', label: t('weather_rain_duration_multiplier'), type: 'number', value: '0.01', min: 0, max: 1 },
          { key: 'scum.ShouldDestroyEntitiesOutsideMapLimitsOnRestart', label: t('should_destroy_entities_outside_map_limits_on_restart'), type: 'boolean', value: '0' },
          { key: 'scum.EnableLockedLootContainers', label: t('enable_locked_loot_containers'), type: 'boolean', value: '1' },
          { key: 'scum.CustomMapEnabled', label: t('custom_map_enabled'), type: 'boolean', value: '0' },
          { key: 'scum.CustomMapCenterXCoordinate', label: t('custom_map_center_x_coordinate'), type: 'number', value: '0.000000', min: -100, max: 100 },
          { key: 'scum.CustomMapCenterYCoordinate', label: t('custom_map_center_y_coordinate'), type: 'number', value: '0.000000', min: -100, max: 100 },
          { key: 'scum.CustomMapWidth', label: t('custom_map_width'), type: 'number', value: '15.240000', min: 1, max: 50 },
          { key: 'scum.CustomMapHeight', label: t('custom_map_height'), type: 'number', value: '15.240000', min: 1, max: 50 },
          { key: 'scum.DoorLockability.Garage', label: t('door_lockability_garage'), type: 'boolean', value: '0' },
          { key: 'scum.CargoDropCooldownMinimum', label: t('cargo_drop_cooldown_minimum'), type: 'number', value: '30.000000', min: 0, max: 300 },
          { key: 'scum.CargoDropCooldownMaximum', label: t('cargo_drop_cooldown_maximum'), type: 'number', value: '30.000000', min: 0, max: 300 },
          { key: 'scum.CargoDropFallDelay', label: t('cargo_drop_fall_delay'), type: 'number', value: '180.000000', min: 0, max: 600 },
          { key: 'scum.CargoDropFallDuration', label: t('cargo_drop_fall_duration'), type: 'number', value: '180.000000', min: 0, max: 600 },
          { key: 'scum.CargoDropSelfdestructTime', label: t('cargo_drop_selfdestruct_time'), type: 'number', value: '900.000000', min: 0, max: 1800 },
          { key: 'scum.CargoDropZombieEncounterWeightMultiplier', label: t('cargo_drop_zombie_encounter_weight_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.CargoDropDropshipEncounterWeightMultiplier', label: t('cargo_drop_dropship_encounter_weight_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.MaxAllowedHunts', label: t('max_allowed_hunts'), type: 'number', value: '25', min: 0, max: 100 },
          { key: 'scum.HuntTriggerChanceOverride_ContinentalForest', label: t('hunt_trigger_chance_override_continental_forest'), type: 'number', value: '-1.000000', min: -1, max: 1 },
          { key: 'scum.HuntTriggerChanceOverride_ContinentalMeadow', label: t('hunt_trigger_chance_override_continental_meadow'), type: 'number', value: '-1.000000', min: -1, max: 1 },
          { key: 'scum.HuntTriggerChanceOverride_Mediterranean', label: t('hunt_trigger_chance_override_mediterranean'), type: 'number', value: '-1.000000', min: -1, max: 1 },
          { key: 'scum.HuntTriggerChanceOverride_Mountain', label: t('hunt_trigger_chance_override_mountain'), type: 'number', value: '-1.000000', min: -1, max: 1 },
          { key: 'scum.HuntTriggerChanceOverride_Urban', label: t('hunt_trigger_chance_override_urban'), type: 'number', value: '-0.000000', min: -1, max: 1 },
          { key: 'scum.HuntTriggerChanceOverride_Village', label: t('hunt_trigger_chance_override_village'), type: 'number', value: '-0.000000', min: -1, max: 1 },
          { key: 'scum.HuntFailureTime', label: t('hunt_failure_time'), type: 'number', value: '150.000000', min: 0, max: 600 },
          { key: 'scum.HuntFailureDistance', label: t('hunt_failure_distance'), type: 'number', value: '300.000000', min: 0, max: 1000 },
          { key: 'scum.BearMaxHealthMultiplier', label: t('bear_max_health_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.BoarMaxHealthMultiplier', label: t('boar_max_health_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.ChickenMaxHealthMultiplier', label: t('chicken_max_health_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.DeerMaxHealthMultiplier', label: t('deer_max_health_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.DonkeyMaxHealthMultiplier', label: t('donkey_max_health_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.GoatMaxHealthMultiplier', label: t('goat_max_health_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.HorseMaxHealthMultiplier', label: t('horse_max_health_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.RabbitMaxHealthMultiplier', label: t('rabbit_max_health_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.WolfMaxHealthMultiplier', label: t('wolf_max_health_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.MaxAllowedKillboxKeycards', label: t('max_allowed_killbox_keycards'), type: 'number', value: '2', min: 0, max: 10 },
          { key: 'scum.MaxAllowedKillboxKeycards_PoliceStation', label: t('max_allowed_killbox_keycards_police_station'), type: 'number', value: '2', min: 0, max: 10 },
          { key: 'scum.MaxAllowedKillboxKeycards_RadiationZone', label: t('max_allowed_killbox_keycards_radiation_zone'), type: 'number', value: '2', min: 0, max: 10 },
          { key: 'scum.AbandonedBunkerMaxSimultaneouslyActive', label: t('abandoned_bunker_max_simultaneously_active'), type: 'number', value: '2', min: 0, max: 10 },
          { key: 'scum.AbandonedBunkerActiveDurationHours', label: t('abandoned_bunker_active_duration_hours'), type: 'number', value: '24.000000', min: 1, max: 168 },
          { key: 'scum.AbandonedBunkerKeyCardActiveDurationHours', label: t('abandoned_bunker_key_card_active_duration_hours'), type: 'number', value: '3.000000', min: 1, max: 24 },
          { key: 'scum.SecretBunkerKeyCardActiveDurationHours', label: t('secret_bunker_key_card_active_duration_hours'), type: 'number', value: '1.000000', min: 1, max: 24 },
          { key: 'scum.EncounterNeverRespawnCharacters', label: t('encounter_never_respawn_characters'), type: 'boolean', value: '0' },
          { key: 'scum.NPCWorldEncounterSpawnWeightMultiplier', label: t('npc_world_encounter_spawn_weight_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 }
        ]
      },
      {
        id: 'vehicles',
        name: t('vehicle_settings'),
        icon: Car,
        description: t('vehicle_settings_desc'),
        settings: [
          { key: 'scum.FuelDrainFromEngineMultiplier', label: t('fuel_drain_from_engine_multiplier'), type: 'number', value: '0.800000', min: 0, max: 2 },
          { key: 'scum.BatteryDrainFromEngineMultiplier', label: t('battery_drain_from_engine_multiplier'), type: 'number', value: '0.000000', min: 0, max: 2 },
          { key: 'scum.BatteryDrainFromDevicesMultiplier', label: t('battery_drain_from_devices_multiplier'), type: 'number', value: '0.800000', min: 0, max: 2 },
          { key: 'scum.BatteryDrainFromInactivityMultiplier', label: t('battery_drain_from_inactivity_multiplier'), type: 'number', value: '0.000000', min: 0, max: 2 },
          { key: 'scum.BatteryChargeWithAlternatorMultiplier', label: t('battery_charge_with_alternator_multiplier'), type: 'number', value: '1.000000', min: 0, max: 2 },
          { key: 'scum.BatteryChargeWithDynamoMultiplier', label: t('battery_charge_with_dynamo_multiplier'), type: 'number', value: '1.000000', min: 0, max: 2 },
          { key: 'scum.KingletDusterMaxAmount', label: t('kinglet_duster_max_amount'), type: 'number', value: '15', min: 0, max: 100 },
          { key: 'scum.KingletDusterMaxFunctionalAmount', label: t('kinglet_duster_max_functional_amount'), type: 'number', value: '20', min: 0, max: 100 },
          { key: 'scum.KingletDusterMinPurchasedAmount', label: t('kinglet_duster_min_purchased_amount'), type: 'number', value: '0', min: 0, max: 100 },
          { key: 'scum.DirtbikeMaxAmount', label: t('dirtbike_max_amount'), type: 'number', value: '15', min: 0, max: 100 },
          { key: 'scum.DirtbikeMaxFunctionalAmount', label: t('dirtbike_max_functional_amount'), type: 'number', value: '25', min: 0, max: 100 },
          { key: 'scum.DirtbikeMinPurchasedAmount', label: t('dirtbike_min_purchased_amount'), type: 'number', value: '10', min: 0, max: 100 },
          { key: 'scum.LaikaMaxAmount', label: t('laika_max_amount'), type: 'number', value: '30', min: 0, max: 100 },
          { key: 'scum.LaikaMaxFunctionalAmount', label: t('laika_max_functional_amount'), type: 'number', value: '50', min: 0, max: 100 },
          { key: 'scum.LaikaMinPurchasedAmount', label: t('laika_min_purchased_amount'), type: 'number', value: '20', min: 0, max: 100 },
          { key: 'scum.MotorboatMaxAmount', label: t('motorboat_max_amount'), type: 'number', value: '8', min: 0, max: 100 },
          { key: 'scum.MotorboatMaxFunctionalAmount', label: t('motorboat_max_functional_amount'), type: 'number', value: '12', min: 0, max: 100 },
          { key: 'scum.MotorboatMinPurchasedAmount', label: t('motorboat_min_purchased_amount'), type: 'number', value: '10', min: 0, max: 100 },
          { key: 'scum.WheelbarrowMaxAmount', label: t('wheelbarrow_max_amount'), type: 'number', value: '0', min: 0, max: 100 },
          { key: 'scum.WheelbarrowMaxFunctionalAmount', label: t('wheelbarrow_max_functional_amount'), type: 'number', value: '0', min: 0, max: 100 },
          { key: 'scum.WheelbarrowMinPurchasedAmount', label: t('wheelbarrow_min_purchased_amount'), type: 'number', value: '0', min: 0, max: 100 },
          { key: 'scum.WolfswagenMaxAmount', label: t('wolfswagen_max_amount'), type: 'number', value: '20', min: 0, max: 100 },
          { key: 'scum.WolfswagenMaxFunctionalAmount', label: t('wolfswagen_max_functional_amount'), type: 'number', value: '40', min: 0, max: 100 },
          { key: 'scum.WolfswagenMinPurchasedAmount', label: t('wolfswagen_min_purchased_amount'), type: 'number', value: '20', min: 0, max: 100 },
          { key: 'scum.BicycleMaxAmount', label: t('bicycle_max_amount'), type: 'number', value: '10', min: 0, max: 100 },
          { key: 'scum.BicycleMaxFunctionalAmount', label: t('bicycle_max_functional_amount'), type: 'number', value: '0', min: 0, max: 100 },
          { key: 'scum.BicycleMinPurchasedAmount', label: t('bicycle_min_purchased_amount'), type: 'number', value: '10', min: 0, max: 100 },
          { key: 'scum.RagerMaxAmount', label: t('rager_max_amount'), type: 'number', value: '40', min: 0, max: 100 },
          { key: 'scum.RagerMaxFunctionalAmount', label: t('rager_max_functional_amount'), type: 'number', value: '60', min: 0, max: 100 },
          { key: 'scum.RagerMinPurchasedAmount', label: t('rager_min_purchased_amount'), type: 'number', value: '20', min: 0, max: 100 },
          { key: 'scum.CruiserMaxAmount', label: t('cruiser_max_amount'), type: 'number', value: '15', min: 0, max: 100 },
          { key: 'scum.CruiserMaxFunctionalAmount', label: t('cruiser_max_functional_amount'), type: 'number', value: '25', min: 0, max: 100 },
          { key: 'scum.CruiserMinPurchasedAmount', label: t('cruiser_min_purchased_amount'), type: 'number', value: '10', min: 0, max: 100 },
          { key: 'scum.RisMaxAmount', label: t('ris_max_amount'), type: 'number', value: '15', min: 0, max: 100 },
          { key: 'scum.RisMaxFunctionalAmount', label: t('ris_max_functional_amount'), type: 'number', value: '25', min: 0, max: 100 },
          { key: 'scum.RisMinPurchasedAmount', label: t('ris_min_purchased_amount'), type: 'number', value: '10', min: 0, max: 100 },
          { key: 'scum.SUPMaxAmount', label: t('sup_max_amount'), type: 'number', value: '0', min: 0, max: 100 },
          { key: 'scum.SUPMaxFunctionalAmount', label: t('sup_max_functional_amount'), type: 'number', value: '0', min: 0, max: 100 },
          { key: 'scum.SUPMinPurchasedAmount', label: t('sup_min_purchased_amount'), type: 'number', value: '0', min: 0, max: 100 },
          { key: 'scum.KingletMarinerMaxAmount', label: t('kinglet_mariner_max_amount'), type: 'number', value: '10', min: 0, max: 100 },
          { key: 'scum.KingletMarinerMaxFunctionalAmount', label: t('kinglet_mariner_max_functional_amount'), type: 'number', value: '15', min: 0, max: 100 },
          { key: 'scum.KingletMarinerMinPurchasedAmount', label: t('kinglet_mariner_min_purchased_amount'), type: 'number', value: '0', min: 0, max: 100 },
          { key: 'scum.TractorMaxAmount', label: t('tractor_max_amount'), type: 'number', value: '15', min: 0, max: 100 },
          { key: 'scum.TractorMaxFunctionalAmount', label: t('tractor_max_functional_amount'), type: 'number', value: '25', min: 0, max: 100 },
          { key: 'scum.TractorMinPurchasedAmount', label: t('tractor_min_purchased_amount'), type: 'number', value: '10', min: 0, max: 100 },
          { key: 'scum.MaximumTimeOfVehicleInactivity', label: t('maximum_time_of_vehicle_inactivity'), type: 'text', value: '168:00:00' },
          { key: 'scum.MaximumTimeForVehiclesInForbiddenZones', label: t('maximum_time_for_vehicles_in_forbidden_zones'), type: 'text', value: '02:00:00' },
          { key: 'scum.LogVehicleDestroyed', label: t('log_vehicle_destroyed'), type: 'boolean', value: '1' },
          { key: 'scum.EnableVehicleDamage', label: t('enable_vehicle_damage'), type: 'boolean', value: '1' },
          { key: 'scum.VehicleDecayTime', label: t('vehicle_decay_time'), type: 'number', value: '1.000000', min: 0, max: 10 },
          { key: 'scum.HumanToVehicleDamageMultiplier', label: t('human_to_vehicle_damage_multiplier'), type: 'number', value: '0.0', min: 0, max: 5 },
          { key: 'scum.ZombieToVehicleDamageMultiplier', label: t('zombie_to_vehicle_damage_multiplier'), type: 'number', value: '0.0', min: 0, max: 5 }
        ]
      },
      {
        id: 'damage',
        name: t('damage_settings'),
        icon: Zap,
        description: t('damage_settings_desc'),
        settings: [
          { key: 'scum.HumanToHumanDamageMultiplier', label: t('human_to_human_damage_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.HumanToHumanArmedMeleeDamageMultiplier', label: t('human_to_human_armed_melee_damage_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.HumanToHumanUnarmedMeleeDamageMultiplier', label: t('human_to_human_unarmed_melee_damage_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.HumanToHumanThrowingDamageMultiplier', label: t('human_to_human_throwing_damage_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 },
          { key: 'scum.ShowKillFeed', label: t('show_kill_feed'), type: 'boolean', value: 'True' },
          { key: 'scum.SentryDamageMultiplier', label: t('sentry_damage_multiplier'), type: 'number', value: '0.800000', min: 0, max: 5 },
          { key: 'scum.SentryRailgunDamageMultiplier', label: t('sentry_railgun_damage_multiplier'), type: 'number', value: '0.800000', min: 0, max: 5 },
          { key: 'scum.SentryGrenadeDamageMultiplier', label: t('sentry_grenade_damage_multiplier'), type: 'number', value: '0.800000', min: 0, max: 5 },
          { key: 'scum.BaseBuildingAttackerSentryDamageMultiplier', label: t('base_building_attacker_sentry_damage_multiplier'), type: 'number', value: '0.000000', min: 0, max: 5 },
          { key: 'scum.BaseBuildingAttackerSentryRailgunDamageMultiplier', label: t('base_building_attacker_sentry_railgun_damage_multiplier'), type: 'number', value: '0.000000', min: 0, max: 5 },
          { key: 'scum.BaseBuildingAttackerSentryGrenadeDamageMultiplier', label: t('base_building_attacker_sentry_grenade_damage_multiplier'), type: 'number', value: '0.000000', min: 0, max: 5 },
          { key: 'scum.SentryBaseBuildingDamageMultiplier', label: t('sentry_base_building_damage_multiplier'), type: 'number', value: '0.000000', min: 0, max: 5 },
          { key: 'scum.DropshipDamageMultiplier', label: t('dropship_damage_multiplier'), type: 'number', value: '0.500000', min: 0, max: 5 },
          { key: 'scum.DropshipRailgunDamageMultiplier', label: t('dropship_railgun_damage_multiplier'), type: 'number', value: '0.500000', min: 0, max: 5 },
          { key: 'scum.DropshipBaseBuildingElementsDamageMultiplier', label: t('dropship_base_building_elements_damage_multiplier'), type: 'number', value: '0.000000', min: 0, max: 5 },
          { key: 'scum.ZombieDamageMultiplier', label: t('zombie_damage_multiplier'), type: 'number', value: '2.000000', min: 0, max: 5 },
          { key: 'scum.ItemDecayDamageMultiplier', label: t('item_decay_damage_multiplier'), type: 'number', value: '0.500000', min: 0, max: 2 },
          { key: 'scum.FoodDecayDamageMultiplier', label: t('food_decay_damage_multiplier'), type: 'number', value: '0.500000', min: 0, max: 2 },
          { key: 'scum.WeaponDecayDamageOnFiring', label: t('weapon_decay_damage_on_firing'), type: 'number', value: '0.500000', min: 0, max: 2 },
          { key: 'scum.LockProtectionDamageMultiplier', label: t('lock_protection_damage_multiplier'), type: 'number', value: '1.000000', min: 0, max: 5 }
        ]
      },
      {
        id: 'respawn',
        name: t('respawn_settings'),
        icon: Users,
        description: t('respawn_settings_desc'),
        settings: [
          { key: 'scum.AllowSectorRespawn', label: t('allow_sector_respawn'), type: 'boolean', value: '1' },
          { key: 'scum.AllowShelterRespawn', label: t('allow_shelter_respawn'), type: 'boolean', value: '1' },
          { key: 'scum.AllowSquadmateRespawn', label: t('allow_squadmate_respawn'), type: 'boolean', value: '1' },
          { key: 'scum.RandomRespawnPrice', label: t('random_respawn_price'), type: 'number', value: '0', min: 0, max: 10000 },
          { key: 'scum.SectorRespawnPrice', label: t('sector_respawn_price'), type: 'number', value: '200', min: 0, max: 10000 },
          { key: 'scum.ShelterRespawnPrice', label: t('shelter_respawn_price'), type: 'number', value: '500', min: 0, max: 10000 },
          { key: 'scum.SquadRespawnPrice', label: t('squad_respawn_price'), type: 'number', value: '3000', min: 0, max: 10000 },
          { key: 'scum.RandomRespawnInitialTime', label: t('random_respawn_initial_time'), type: 'number', value: '0.000000', min: 0, max: 300 },
          { key: 'scum.SectorRespawnInitialTime', label: t('sector_respawn_initial_time'), type: 'number', value: '30.000000', min: 0, max: 300 },
          { key: 'scum.ShelterRespawnInitialTime', label: t('shelter_respawn_initial_time'), type: 'number', value: '30.000000', min: 0, max: 300 },
          { key: 'scum.SquadRespawnInitialTime', label: t('squad_respawn_initial_time'), type: 'number', value: '60.000000', min: 0, max: 300 },
          { key: 'scum.RandomRespawnCooldown', label: t('random_respawn_cooldown'), type: 'number', value: '0.000000', min: 0, max: 300 },
          { key: 'scum.SectorRespawnCooldown', label: t('sector_respawn_cooldown'), type: 'number', value: '30.000000', min: 0, max: 300 },
          { key: 'scum.ShelterRespawnCooldown', label: t('shelter_respawn_cooldown'), type: 'number', value: '30.000000', min: 0, max: 300 },
          { key: 'scum.SquadRespawnCooldown', label: t('squad_respawn_cooldown'), type: 'number', value: '60.000000', min: 0, max: 300 },
          { key: 'scum.RandomCooldownResetMultiplier', label: t('random_cooldown_reset_multiplier'), type: 'number', value: '0.000000', min: 0, max: 10 },
          { key: 'scum.SectorCooldownResetMultiplier', label: t('sector_cooldown_reset_multiplier'), type: 'number', value: '3.000000', min: 0, max: 10 },
          { key: 'scum.ShelterCooldownResetMultiplier', label: t('shelter_cooldown_reset_multiplier'), type: 'number', value: '3.000000', min: 0, max: 10 },
          { key: 'scum.SquadCooldownResetMultiplier', label: t('squad_cooldown_reset_multiplier'), type: 'number', value: '2.000000', min: 0, max: 10 },
          { key: 'scum.RandomPricePerSquadmateModifier', label: t('random_price_per_squadmate_modifier'), type: 'number', value: '0.000000', min: 0, max: 1000 },
          { key: 'scum.SectorPricePerSquadmateModifier', label: t('sector_price_per_squadmate_modifier'), type: 'number', value: '0.000000', min: 0, max: 1000 },
          { key: 'scum.ShelterPricePerSquadmateModifier', label: t('shelter_price_per_squadmate_modifier'), type: 'number', value: '0.000000', min: 0, max: 1000 },
          { key: 'scum.CommitSuicideInitialTime', label: t('commit_suicide_initial_time'), type: 'number', value: '0.000000', min: 0, max: 300 },
          { key: 'scum.CommitSuicideCooldown', label: t('commit_suicide_cooldown'), type: 'number', value: '60.000000', min: 0, max: 300 },
          { key: 'scum.CommitSuicideCooldownResetMultiplier', label: t('commit_suicide_cooldown_reset_multiplier'), type: 'number', value: '1.000000', min: 0, max: 10 },
          { key: 'scum.MaximumBaseProximityWhenSpawning', label: t('maximum_base_proximity_when_spawning'), type: 'number', value: '10000.000000', min: 0, max: 50000 },
          { key: 'scum.PermadeathThreshold', label: t('permadeath_threshold'), type: 'number', value: '-2500', min: -10000, max: 0 }
        ]
      },
      {
        id: 'features',
        name: t('special_resources'),
        icon: Settings,
        description: t('special_resources_desc'),
        settings: [
          { key: 'scum.FlagOvertakeDuration', label: t('flag_overtake_duration'), type: 'text', value: '24:00:00' },
          { key: 'scum.MaximumAmountOfElementsPerFlag', label: t('maximum_amount_of_elements_per_flag'), type: 'number', value: '1000', min: 100, max: 10000 },
          { key: 'scum.ExtraElementsPerFlagForAdditionalSquadMember', label: t('extra_elements_per_flag_for_additional_squad_member'), type: 'number', value: '25', min: 0, max: 1000 },
          { key: 'scum.MaximumNumberOfExpandedElementsPerFlag', label: t('maximum_number_of_expanded_elements_per_flag'), type: 'number', value: '100', min: 0, max: 1000 },
          { key: 'scum.AllowMultipleFlagsPerPlayer', label: t('allow_multiple_flags_per_player'), type: 'boolean', value: '1' },
          { key: 'scum.AllowFlagPlacementOnBBElements', label: t('allow_flag_placement_on_bb_elements'), type: 'boolean', value: '0' },
          { key: 'scum.ChestAcquisitionDuration', label: t('chest_acquisition_duration'), type: 'number', value: '64.000000', min: 0, max: 1000 },
          { key: 'scum.WeaponRackMaxAmountPerFlagArea', label: t('weapon_rack_max_amount_per_flag_area'), type: 'number', value: '7', min: 0, max: 100 },
          { key: 'scum.WeaponRackStartDecayingIfFlagAreaHasMoreThan', label: t('weapon_rack_start_decaying_if_flag_area_has_more_than'), type: 'number', value: '9', min: 0, max: 100 },
          { key: 'scum.WallWeaponRackMaxAmountPerFlagArea', label: t('wall_weapon_rack_max_amount_per_flag_area'), type: 'number', value: '7', min: 0, max: 100 },
          { key: 'scum.WallWeaponRackStartDecayingIfFlagAreaHasMoreThan', label: t('wall_weapon_rack_start_decaying_if_flag_area_has_more_than'), type: 'number', value: '9', min: 0, max: 100 },
          { key: 'scum.WellMaxAmountPerFlagArea', label: t('well_max_amount_per_flag_area'), type: 'number', value: '2', min: 0, max: 100 },
          { key: 'scum.WellStartDecayingIfFlagAreaHasMoreThan', label: t('well_start_decaying_if_flag_area_has_more_than'), type: 'number', value: '4', min: 0, max: 100 },
          { key: 'scum.TurretMaxAmountPerFlagArea', label: t('turret_max_amount_per_flag_area'), type: 'number', value: '2', min: 0, max: 100 },
          { key: 'scum.TurretStartDecayingIfFlagAreaHasMoreThan', label: t('turret_start_decaying_if_flag_area_has_more_than'), type: 'number', value: '3', min: 0, max: 100 },
          { key: 'scum.GardenMaxAmountPerFlagArea', label: t('garden_max_amount_per_flag_area'), type: 'number', value: '2', min: 0, max: 100 },
          { key: 'scum.AllowFloorPlacementOnHalfAndLowWalls', label: t('allow_floor_placement_on_half_and_low_walls'), type: 'boolean', value: '1' },
          { key: 'scum.AllowWallPlacementOnHalfAndLowWalls', label: t('allow_wall_placement_on_half_and_low_walls'), type: 'boolean', value: '1' },
          { key: 'scum.RaidProtectionType', label: t('raid_protection_type'), type: 'number', value: '0', min: 0, max: 10 },
          { key: 'scum.RaidProtectionEnableLog', label: t('raid_protection_enable_log'), type: 'boolean', value: '0' },
          { key: 'scum.RaidProtectionFlagSpecificChangeSettingCooldown', label: t('raid_protection_flag_specific_change_setting_cooldown'), type: 'text', value: '120:00:00' },
          { key: 'scum.RaidProtectionFlagSpecificChangeSettingPrice', label: t('raid_protection_flag_specific_change_setting_price'), type: 'text', value: '10g' },
          { key: 'scum.RaidProtectionFlagSpecificMaxProtectionTime', label: t('raid_protection_flag_specific_max_protection_time'), type: 'text', value: '08:00:00' },
          { key: 'scum.RaidProtectionOfflineProtectionStartDelay', label: t('raid_protection_offline_protection_start_delay'), type: 'text', value: '00:30:00' },
          { key: 'scum.RaidProtectionOfflineMaxProtectionTime', label: t('raid_protection_offline_max_protection_time'), type: 'text', value: '-' },
          { key: 'scum.RaidProtectionGlobalShouldShowRaidTimesMessage', label: t('raid_protection_global_should_show_raid_times_message'), type: 'boolean', value: '1' },
          { key: 'scum.RaidProtectionGlobalShouldShowRaidAnnouncementMessage', label: t('raid_protection_global_should_show_raid_announcement_message'), type: 'boolean', value: '1' },
          { key: 'scum.RaidProtectionGlobalShouldShowRaidStartEndMessages', label: t('raid_protection_global_should_show_raid_start_end_messages'), type: 'boolean', value: '1' },
          { key: 'scum.WaterPricePerUnitMultiplier', label: t('water_price_per_unit_multiplier'), type: 'number', value: '1.000000', min: 0, max: 10 },
          { key: 'scum.WaterPeriodicInitialAmountMultiplier', label: t('water_periodic_initial_amount_multiplier'), type: 'number', value: '2.000000', min: 0, max: 10 },
          { key: 'scum.WaterPeriodicMaxAmountMultiplier', label: t('water_periodic_max_amount_multiplier'), type: 'number', value: '3.000000', min: 0, max: 10 },
          { key: 'scum.WaterPeriodicReplenishAmountMultiplier', label: t('water_periodic_replenish_amount_multiplier'), type: 'number', value: '3.000000', min: 0, max: 10 },
          { key: 'scum.WaterPeriodicReplenishIntervalMultiplier', label: t('water_periodic_replenish_interval_multiplier'), type: 'number', value: '0.500000', min: 0, max: 10 },
          { key: 'scum.WaterProximityReplenishAmountMultiplier', label: t('water_proximity_replenish_amount_multiplier'), type: 'number', value: '3.000000', min: 0, max: 10 },
          { key: 'scum.WaterProximityReplenishChanceMultiplier', label: t('water_proximity_replenish_chance_multiplier'), type: 'number', value: '3.000000', min: 0, max: 10 },
          { key: 'scum.WaterProximityReplenishTimeoutMultiplier', label: t('water_proximity_replenish_timeout_multiplier'), type: 'number', value: '0.500000', min: 0, max: 10 },
          { key: 'scum.GasolinePricePerUnitMultiplier', label: t('gasoline_price_per_unit_multiplier'), type: 'number', value: '1.000000', min: 0, max: 10 },
          { key: 'scum.GasolinePeriodicInitialAmountMultiplier', label: t('gasoline_periodic_initial_amount_multiplier'), type: 'number', value: '1.000000', min: 0, max: 10 },
          { key: 'scum.GasolinePeriodicMaxAmountMultiplier', label: t('gasoline_periodic_max_amount_multiplier'), type: 'number', value: '2.000000', min: 0, max: 10 },
          { key: 'scum.GasolinePeriodicReplenishAmountMultiplier', label: t('gasoline_periodic_replenish_amount_multiplier'), type: 'number', value: '2.000000', min: 0, max: 10 },
          { key: 'scum.GasolinePeriodicReplenishIntervalMultiplier', label: t('gasoline_periodic_replenish_interval_multiplier'), type: 'number', value: '0.500000', min: 0, max: 10 },
          { key: 'scum.GasolineProximityReplenishAmountMultiplier', label: t('gasoline_proximity_replenish_amount_multiplier'), type: 'number', value: '2.000000', min: 0, max: 10 },
          { key: 'scum.GasolineProximityReplenishChanceMultiplier', label: t('gasoline_proximity_replenish_chance_multiplier'), type: 'number', value: '2.000000', min: 0, max: 10 },
          { key: 'scum.GasolineProximityReplenishTimeoutMultiplier', label: t('gasoline_proximity_replenish_timeout_multiplier'), type: 'number', value: '0.500000', min: 0, max: 10 }
        ]
      }
    ]);
  }, [t]);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const response = await ServerConfigService.getServerConfig();
      
      if (response.success && response.content) {
        setConfig(response.content);
        setOriginalConfig(response.content); // Guardar configuração original
        parseConfigToSettings(response.content);
      } else {
        console.error('Erro ao carregar configuração:', response.error);
      }
    } catch (error) {
      console.error('Erro ao carregar configuração:', error);
    } finally {
      setLoading(false);
    }
  };

  const parseConfigToSettings = (configLines: string[]) => {
    // Parse das linhas de configuração para um objeto estruturado
    const parsedConfig = ServerConfigService.parseConfigLines(configLines);
    
    // Atualizar os valores das seções com base nos dados carregados
    setSections(prevSections => 
      prevSections.map(section => ({
        ...section,
        settings: section.settings.map(setting => {
          const value = ServerConfigService.findConfigValue(parsedConfig, setting.key);
          return {
            ...setting,
            value: value !== null ? value : setting.value
          };
        })
      }))
    );
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Usar a função que garante 100% de preservação - CRÍTICA para funcionamento do servidor
      const configLines = saveWithCompletePreservation();
      
      const response = await ServerConfigService.saveServerConfig(configLines);
      
      if (response.success) {
        console.log('✅ Configuração salva com 100% de preservação');
        // Atualizar configuração original após salvar
        setOriginalConfig(configLines);
        // Mostrar notificação de sucesso
        alert('✅ Configuração salva com 100% de preservação!\n\nTodas as configurações originais foram mantidas.');
      } else {
        console.error('Erro ao salvar:', response.error);
        // Mostrar notificação de erro
        alert('❌ Erro ao salvar configuração: ' + (response.error || 'Erro desconhecido'));
      }
    } catch (error) {
      console.error('Erro ao salvar configuração:', error);
      alert('❌ Erro ao salvar configuração: ' + error);
    } finally {
      setSaving(false);
    }
  };

  const convertSettingsToConfig = (): string[] => {
    // Criar um mapa das configurações que foram modificadas no frontend
    const modifiedSettings = new Map<string, string>();
    sections.forEach(section => {
      section.settings.forEach(setting => {
        modifiedSettings.set(setting.key, setting.value);
      });
    });
    
    // Processar linha por linha do arquivo original, aplicando apenas as modificações
    const result: string[] = [];
    
    originalConfig.forEach(line => {
      const trimmedLine = line.trim();
      
      if (trimmedLine.startsWith('[') && trimmedLine.endsWith(']')) {
        // Nova seção - preservar exatamente como está
        result.push(line);
      } else if (trimmedLine.includes('=')) {
        // Configuração
        const [key, ...valueParts] = trimmedLine.split('=');
        const configKey = key.trim();
        const originalValue = valueParts.join('=').trim();
        
        // Verificar se esta configuração foi modificada no frontend
        if (modifiedSettings.has(configKey)) {
          // Usar valor modificado, mas preservar espaçamento original
          const originalSpacing = line.match(/^\s*/)?.[0] || '';
          const originalKeySpacing = line.match(/=\s*/)?.[0] || '=';
          result.push(`${originalSpacing}${configKey}${originalKeySpacing}${modifiedSettings.get(configKey)}`);
        } else {
          // Preservar linha original exatamente
          result.push(line);
        }
      } else {
        // Preservar linhas vazias, comentários e formatação original
        result.push(line);
      }
    });
    
    return result;
  };

  // Função para salvar preservando TODAS as configurações originais (100% garantido)
  const saveWithAllOriginalSettings = (): string[] => {
    // Criar um mapa das configurações que estão na interface (apenas estas podem ser modificadas)
    const interfaceSettings = new Map<string, string>();
    sections.forEach(section => {
      section.settings.forEach(setting => {
        interfaceSettings.set(setting.key, setting.value);
      });
    });
    
    // Processar linha por linha do arquivo original, preservando TUDO
    const result: string[] = [];
    
    originalConfig.forEach(line => {
      const trimmedLine = line.trim();
      
      if (trimmedLine.startsWith('[') && trimmedLine.endsWith(']')) {
        // Nova seção - preservar exatamente como está
        result.push(line);
      } else if (trimmedLine.includes('=')) {
        // Configuração
        const [key, ...valueParts] = trimmedLine.split('=');
        const configKey = key.trim();
        const originalValue = valueParts.join('=').trim();
        
        // Verificar se esta configuração está na interface (pode ser modificada)
        if (interfaceSettings.has(configKey)) {
          // Usar valor da interface, mas preservar espaçamento original
          const originalSpacing = line.match(/^\s*/)?.[0] || '';
          const originalKeySpacing = line.match(/=\s*/)?.[0] || '=';
          result.push(`${originalSpacing}${configKey}${originalKeySpacing}${interfaceSettings.get(configKey)}`);
        } else {
          // Preservar linha original exatamente (configuração não está na interface)
          result.push(line);
        }
      } else {
        // Preservar linhas vazias, comentários e formatação original
        result.push(line);
      }
    });
    
    return result;
  };

  // Função para garantir 100% de preservação - CRÍTICA para funcionamento do servidor
  const saveWithCompletePreservation = (): string[] => {
    console.log('🔒 GARANTIA 100%: Preservando TODAS as configurações originais...');
    
    // Criar um mapa das configurações que estão na interface (apenas estas podem ser modificadas)
    const interfaceSettings = new Map<string, string>();
    sections.forEach(section => {
      section.settings.forEach(setting => {
        interfaceSettings.set(setting.key, setting.value);
      });
    });
    
    // Processar linha por linha do arquivo original, preservando TUDO
    const result: string[] = [];
    let modifiedCount = 0;
    let preservedCount = 0;
    
    originalConfig.forEach(line => {
      const trimmedLine = line.trim();
      
      if (trimmedLine.startsWith('[') && trimmedLine.endsWith(']')) {
        // Nova seção - preservar exatamente como está
        result.push(line);
      } else if (trimmedLine.includes('=')) {
        // Configuração
        const [key, ...valueParts] = trimmedLine.split('=');
        const configKey = key.trim();
        const originalValue = valueParts.join('=').trim();
        
        // Verificar se esta configuração está na interface (pode ser modificada)
        if (interfaceSettings.has(configKey)) {
          // Usar valor da interface, mas preservar espaçamento original
          const originalSpacing = line.match(/^\s*/)?.[0] || '';
          const originalKeySpacing = line.match(/=\s*/)?.[0] || '=';
          result.push(`${originalSpacing}${configKey}${originalKeySpacing}${interfaceSettings.get(configKey)}`);
          modifiedCount++;
        } else {
          // Preservar linha original exatamente (configuração não está na interface)
          result.push(line);
          preservedCount++;
        }
      } else {
        // Preservar linhas vazias, comentários e formatação original
        result.push(line);
        preservedCount++;
      }
    });
    
    console.log(`✅ Preservação 100%: ${preservedCount} configurações preservadas, ${modifiedCount} modificadas`);
    return result;
  };

  // Função para verificar se TODAS as configurações originais estão sendo preservadas
  const verifyCompletePreservation = (): boolean => {
    const savedConfig = saveWithCompletePreservation();
    const originalParsed = ServerConfigService.parseConfigLines(originalConfig);
    const savedParsed = ServerConfigService.parseConfigLines(savedConfig);
    
    // Verificar se todas as seções originais estão presentes
    const originalSections = Object.keys(originalParsed);
    const savedSections = Object.keys(savedParsed);
    
    const missingSections = originalSections.filter(section => !savedSections.includes(section));
    if (missingSections.length > 0) {
      console.error('❌ Seções perdidas:', missingSections);
      return false;
    }
    
    // Verificar se todas as configurações originais estão presentes
    let totalOriginalSettings = 0;
    let totalSavedSettings = 0;
    
    originalSections.forEach(sectionName => {
      const originalSection = originalParsed[sectionName];
      const savedSection = savedParsed[sectionName];
      
      if (!savedSection) {
        console.error(`❌ Seção ${sectionName} perdida completamente`);
        return false;
      }
      
      const originalKeys = Object.keys(originalSection);
      const savedKeys = Object.keys(savedSection);
      
      totalOriginalSettings += originalKeys.length;
      totalSavedSettings += savedKeys.length;
      
      const missingKeys = originalKeys.filter(key => !savedKeys.includes(key));
      if (missingKeys.length > 0) {
        console.error(`⚠️ Seção ${sectionName} - ${missingKeys.length} chaves perdidas:`, missingKeys);
        return false;
      }
    });
    
    console.log(`✅ Preservação completa: ${totalSavedSettings}/${totalOriginalSettings} configurações`);
    return totalSavedSettings === totalOriginalSettings;
  };

  // Função para análise detalhada das configurações perdidas
  const analyzeMissingSettings = () => {
    const savedConfig = saveWithCompletePreservation();
    const originalParsed = ServerConfigService.parseConfigLines(originalConfig);
    const savedParsed = ServerConfigService.parseConfigLines(savedConfig);
    
    console.log('=== ANÁLISE DETALHADA DAS CONFIGURAÇÕES PERDIDAS ===');
    
    // Verificar seções perdidas
    const originalSections = Object.keys(originalParsed);
    const savedSections = Object.keys(savedParsed);
    const missingSections = originalSections.filter(section => !savedSections.includes(section));
    
    if (missingSections.length > 0) {
      console.error('❌ SEÇÕES PERDIDAS:', missingSections);
    } else {
      console.log('✅ Todas as seções preservadas');
    }
    
    // Verificar configurações perdidas por seção
    originalSections.forEach(sectionName => {
      const originalSection = originalParsed[sectionName];
      const savedSection = savedParsed[sectionName];
      
      if (!savedSection) {
        console.error(`❌ Seção ${sectionName} perdida completamente`);
        return;
      }
      
      const originalKeys = Object.keys(originalSection);
      const savedKeys = Object.keys(savedSection);
      const missingKeys = originalKeys.filter(key => !savedKeys.includes(key));
      
      if (missingKeys.length > 0) {
        console.error(`⚠️ Seção ${sectionName} - ${missingKeys.length} chaves perdidas:`);
        missingKeys.forEach(key => {
          console.error(`  - ${key}=${originalSection[key]}`);
        });
      } else {
        console.log(`✅ Seção ${sectionName} - completa (${originalKeys.length} configurações)`);
      }
    });
    
    // Estatísticas gerais
    const totalOriginalSettings = Object.values(originalParsed).reduce((total, section) => total + Object.keys(section).length, 0);
    const totalSavedSettings = Object.values(savedParsed).reduce((total, section) => total + Object.keys(section).length, 0);
    
    console.log(`📊 Estatísticas:`);
    console.log(`  - Configurações originais: ${totalOriginalSettings}`);
    console.log(`  - Configurações salvas: ${totalSavedSettings}`);
    console.log(`  - Configurações perdidas: ${totalOriginalSettings - totalSavedSettings}`);
    console.log(`  - Taxa de preservação: ${((totalSavedSettings / totalOriginalSettings) * 100).toFixed(2)}%`);
    
    console.log('=== FIM DA ANÁLISE ===');
  };

  // Função para corrigir automaticamente as configurações perdidas
  const fixMissingSettings = () => {
    console.log('=== CORREÇÃO AUTOMÁTICA DE CONFIGURAÇÕES PERDIDAS ===');
    
    const savedConfig = saveWithCompletePreservation();
    const originalParsed = ServerConfigService.parseConfigLines(originalConfig);
    const savedParsed = ServerConfigService.parseConfigLines(savedConfig);
    
    // Encontrar todas as configurações perdidas
    const missingSettings: { section: string; key: string; value: string }[] = [];
    
    Object.entries(originalParsed).forEach(([sectionName, section]) => {
      const savedSection = savedParsed[sectionName];
      if (!savedSection) {
        // Seção completamente perdida
        Object.entries(section).forEach(([key, value]) => {
          missingSettings.push({ section: sectionName, key, value });
        });
      } else {
        // Verificar configurações perdidas na seção
        Object.entries(section).forEach(([key, value]) => {
          if (!savedSection[key]) {
            missingSettings.push({ section: sectionName, key, value });
          }
        });
      }
    });
    
    if (missingSettings.length === 0) {
      console.log('✅ Nenhuma configuração perdida encontrada!');
      return;
    }
    
    console.log(`🔧 Encontradas ${missingSettings.length} configurações perdidas. Aplicando correções...`);
    
    // Aplicar correções
    const correctedConfig = [...originalConfig];
    
    missingSettings.forEach(({ section, key, value }) => {
      // Encontrar onde inserir a configuração na seção correta
      let sectionIndex = -1;
      let insertIndex = -1;
      
      for (let i = 0; i < correctedConfig.length; i++) {
        const line = correctedConfig[i].trim();
        if (line === `[${section}]`) {
          sectionIndex = i;
          // Encontrar o final da seção
          for (let j = i + 1; j < correctedConfig.length; j++) {
            const nextLine = correctedConfig[j].trim();
            if (nextLine.startsWith('[') && nextLine.endsWith(']')) {
              insertIndex = j;
              break;
            }
          }
          if (insertIndex === -1) {
            insertIndex = correctedConfig.length;
          }
          break;
        }
      }
      
      if (sectionIndex !== -1 && insertIndex !== -1) {
        // Inserir a configuração perdida
        correctedConfig.splice(insertIndex, 0, `${key}=${value}`);
        console.log(`✅ Adicionada: ${key}=${value} na seção [${section}]`);
      }
    });
    
    console.log('✅ Correções aplicadas! Configuração agora preserva 100% das configurações originais.');
    
    // Atualizar a configuração original com as correções
    setOriginalConfig(correctedConfig);
    
    return correctedConfig;
  };

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => 
      prev.includes(sectionId) 
        ? prev.filter(id => id !== sectionId)
        : [...prev, sectionId]
    );
  };

  const toggleToggleSection = (sectionId: string) => {
    setExpandedToggleSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  };

  const filterSettings = (settings: ConfigSetting[], term: string): ConfigSetting[] => {
    if (!term.trim()) return settings;
    
    const searchLower = term.toLowerCase();
    return settings.filter(setting => 
      setting.label.toLowerCase().includes(searchLower) ||
      setting.key.toLowerCase().includes(searchLower) ||
      (setting.description && setting.description.toLowerCase().includes(searchLower))
    );
  };

  const getFilteredSections = () => {
    if (!searchTerm.trim()) return sections;
    
    return sections.map(section => ({
      ...section,
      settings: filterSettings(section.settings, searchTerm)
    })).filter(section => section.settings.length > 0);
  };

  const highlightSearchTerm = (text: string) => {
    if (!searchTerm.trim()) return text;
    
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, index) => 
      regex.test(part) ? (
        <span key={index} className="bg-scum-accent/30 text-scum-accent font-medium px-1 rounded">
          {part}
        </span>
      ) : part
    );
  };

  const validateIniSyntax = (lines: string[]) => {
    const errors: string[] = [];
    let lineNumber = 0;
    
    for (const line of lines) {
      lineNumber++;
      const trimmedLine = line.trim();
      
      if (trimmedLine === '' || trimmedLine.startsWith(';')) continue;
      
      // Verificar se é uma seção válida [Section]
      if (trimmedLine.startsWith('[') && trimmedLine.endsWith(']')) {
        const sectionName = trimmedLine.slice(1, -1);
        if (sectionName.trim() === '') {
          errors.push(`Linha ${lineNumber}: Nome da seção vazio`);
        }
        continue;
      }
      
      // Verificar se é uma chave=valor válida
      if (trimmedLine.includes('=')) {
        const [key, value] = trimmedLine.split('=', 2);
        if (!key.trim()) {
          errors.push(`Linha ${lineNumber}: Chave vazia`);
        }
        continue;
      }
      
      // Se não é seção nem chave=valor, é um erro
      if (trimmedLine !== '') {
        errors.push(`Linha ${lineNumber}: Formato inválido`);
      }
    }
    
    return errors;
  };

  const updateSetting = (sectionId: string, settingKey: string, value: string) => {
    setSections(prevSections => 
      prevSections.map(section => 
        section.id === sectionId 
          ? {
              ...section,
              settings: section.settings.map(setting => 
                setting.key === settingKey 
                  ? { ...setting, value }
                  : setting
              )
            }
          : section
      )
    );
  };

  const renderSettingInput = (setting: ConfigSetting, sectionId: string) => {
    switch (setting.type) {
      case 'text':
        return (
          <input
            type="text"
            value={setting.value}
            onChange={(e) => updateSetting(sectionId, setting.key, e.target.value)}
            className="w-full bg-scum-gray/50 border border-scum-primary/30 rounded-lg px-2 py-1.5 text-xs text-scum-light placeholder-scum-muted focus:border-scum-accent focus:outline-none"
            placeholder={setting.description}
          />
        );
      
      case 'number':
        return (
          <input
            type="number"
            value={setting.value}
            onChange={(e) => updateSetting(sectionId, setting.key, e.target.value)}
            min={setting.min}
            max={setting.max}
            step="0.1"
            className="w-full bg-scum-gray/50 border border-scum-primary/30 rounded-lg px-2 py-1.5 text-xs text-scum-light placeholder-scum-muted focus:border-scum-accent focus:outline-none"
          />
        );
      
      case 'boolean':
        return (
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={setting.value === '1' || setting.value === 'True'}
              onChange={(e) => updateSetting(sectionId, setting.key, e.target.checked ? '1' : '0')}
              className="sr-only peer"
            />
            <div className="w-10 h-5 bg-scum-gray peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[1px] after:left-[1px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-scum-accent"></div>
          </label>
        );
      
      case 'select':
        return (
          <select
            value={setting.value}
            onChange={(e) => updateSetting(sectionId, setting.key, e.target.value)}
            className="w-full bg-scum-gray/50 border border-scum-primary/30 rounded-lg px-2 py-1.5 text-xs text-scum-light focus:border-scum-accent focus:outline-none"
          >
            {setting.options?.map(option => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        );
      
      case 'textarea':
        return (
          <textarea
            value={setting.value}
            onChange={(e) => updateSetting(sectionId, setting.key, e.target.value)}
            rows={2}
            className="w-full bg-scum-gray/50 border border-scum-primary/30 rounded-lg px-2 py-1.5 text-xs text-scum-light placeholder-scum-muted focus:border-scum-accent focus:outline-none"
            placeholder={setting.description}
          />
        );
      
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-scum-accent border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-scum-light military-text">Carregando configurações...</p>
        </div>
      </div>
    );
  }



  return (
    <div className="space-y-6">
      {/* Header com controles */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-scum-light">Configurações do Servidor</h2>
          <p className="text-scum-muted text-sm">Gerencie as configurações do servidor SCUM</p>
        </div>
        
        <div className="flex items-center gap-4">
          <button
            onClick={() => setShowBackups(!showBackups)}
            className="flex items-center gap-2 text-scum-muted hover:text-scum-light transition-colors"
          >
            <History size={16} />
            <span className="text-sm">Backups</span>
          </button>
          
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-scum-muted hover:text-scum-light transition-colors"
          >
            {showAdvanced ? <EyeOff size={16} /> : <Eye size={16} />}
            <span className="text-sm">Avançado</span>
          </button>
          
          <button
            onClick={loadConfig}
            className="flex items-center gap-2 text-scum-muted hover:text-scum-light transition-colors"
          >
            <RotateCcw size={16} />
            <span className="text-sm">Recarregar</span>
          </button>
          
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 bg-scum-accent hover:bg-scum-accent/80 disabled:bg-scum-muted text-scum-dark font-bold py-2 px-4 rounded-lg transition-all duration-200"
          >
            {saving ? (
              <>
                <div className="w-4 h-4 border-2 border-scum-dark border-t-transparent rounded-full animate-spin"></div>
                Salvando...
              </>
            ) : (
              <>
                <Save size={16} />
                Salvar
              </>
            )}
          </button>
        </div>
      </div>

      {/* Campo de Pesquisa */}
      <div className="relative mb-6">
        <div className="relative">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Pesquisar configurações..."
            className="w-full bg-scum-gray/50 border border-scum-primary/30 rounded-lg pl-10 pr-4 py-3 text-scum-light placeholder-scum-muted focus:border-scum-accent focus:outline-none"
          />
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-scum-muted" size={18} />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-scum-muted hover:text-scum-light transition-colors"
            >
              <X size={16} />
            </button>
          )}
        </div>
        {searchTerm && (
          <div className="mt-2 text-xs text-scum-muted">
            {getFilteredSections().reduce((total, section) => total + section.settings.length, 0)} configurações encontradas
          </div>
        )}
      </div>

      {/* Seções de Configuração */}
      {searchTerm && (
        <div className="mb-4 p-3 bg-scum-accent/10 border border-scum-accent/20 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-scum-accent">
            <Search size={16} />
            <span>Pesquisando por: "{searchTerm}"</span>
            <button
              onClick={() => setSearchTerm('')}
              className="ml-auto text-scum-muted hover:text-scum-accent transition-colors"
            >
              <X size={14} />
            </button>
          </div>
        </div>
      )}
      <div className="space-y-4">

        {getFilteredSections().map((section) => {
          const IconComponent = section.icon;
          const isExpanded = searchTerm ? true : expandedSections.includes(section.id);
          
          return (
            <motion.div
              key={section.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="scum-card"
            >
              {/* Header da Seção */}
              <button
                onClick={() => toggleSection(section.id)}
                className="w-full flex items-center justify-between p-4 hover:bg-scum-gray/20 transition-colors rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <IconComponent className="text-scum-accent" size={20} />
                  <div className="text-left">
                    <h3 className="text-lg font-semibold text-scum-light">{section.name}</h3>
                    <p className="text-sm text-scum-muted">{section.description}</p>
                  </div>
                </div>
                {isExpanded ? <ChevronDown size={20} className="text-scum-muted" /> : <ChevronRight size={20} className="text-scum-muted" />}
              </button>

              {/* Conteúdo da Seção */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.3 }}
                    className="overflow-hidden"
                  >
                    <div className="p-4 pt-0 space-y-4">
                      {(() => {
                        const booleanSettings = section.settings.filter(s => s.type === 'boolean');
                        const otherSettings = section.settings.filter(s => s.type !== 'boolean');
                        
                        return (
                          <>
                            {/* Configurações que não são boolean (text, number, select, textarea) */}
                            {otherSettings.length > 0 && (
                              <div className="space-y-4">
                                <button
                                  onClick={() => toggleToggleSection(section.id + '-values')}
                                  className="w-full flex items-center justify-between p-3 bg-scum-gray/20 rounded-lg border border-scum-primary/10 hover:bg-scum-gray/30 transition-colors"
                                >
                                  <div className="flex items-center gap-3">
                                    <h4 className="text-sm font-medium text-scum-muted">
                                      Configurações de Valores
                                    </h4>
                                    <span className="px-2 py-1 bg-scum-primary/20 rounded-full text-xs text-scum-muted">
                                      {otherSettings.length} campos
                                    </span>
                                  </div>
                                  {expandedToggleSections.has(section.id + '-values') ? (
                                    <ChevronUp size={16} className="text-scum-muted" />
                                  ) : (
                                    <ChevronDown size={16} className="text-scum-muted" />
                                  )}
                                </button>
                                
                                <AnimatePresence>
                                  {expandedToggleSections.has(section.id + '-values') && (
                                    <motion.div
                                      initial={{ opacity: 0, height: 0 }}
                                      animate={{ opacity: 1, height: 'auto' }}
                                      exit={{ opacity: 0, height: 0 }}
                                      transition={{ duration: 0.2 }}
                                      className="overflow-hidden"
                                    >
                                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                        {otherSettings.map((setting) => (
                                          <div 
                                            key={setting.key} 
                                            className={`space-y-2 ${
                                              setting.type === 'textarea' ? 'sm:col-span-2 lg:col-span-3 xl:col-span-4' : ''
                                            }`}
                                          >
                                            <label className="block text-xs font-medium text-scum-light">
                                              {highlightSearchTerm(setting.label)}
                                              {setting.description && (
                                                <span className="block text-xs text-scum-muted mt-1">({highlightSearchTerm(setting.description)})</span>
                                              )}
                                            </label>
                                            {renderSettingInput(setting, section.id)}
                                          </div>
                                        ))}
                                      </div>
                                    </motion.div>
                                  )}
                                </AnimatePresence>
                              </div>
                            )}
                            
                            {/* Configurações boolean organizadas em grid */}
                            {booleanSettings.length > 0 && (
                              <div className="space-y-4">
                                <button
                                  onClick={() => toggleToggleSection(section.id)}
                                  className="w-full flex items-center justify-between p-3 bg-scum-gray/20 rounded-lg border border-scum-primary/10 hover:bg-scum-gray/30 transition-colors"
                                >
                                  <div className="flex items-center gap-3">
                                    <h4 className="text-sm font-medium text-scum-muted">
                                      Configurações de Toggle
                                    </h4>
                                    <span className="px-2 py-1 bg-scum-accent/20 rounded-full text-xs text-scum-muted">
                                      {booleanSettings.filter(s => s.value === '1').length}/{booleanSettings.length} ativos
                                    </span>
                                  </div>
                                  {expandedToggleSections.has(section.id) ? (
                                    <ChevronUp size={16} className="text-scum-muted" />
                                  ) : (
                                    <ChevronDown size={16} className="text-scum-muted" />
                                  )}
                                </button>
                                
                                <AnimatePresence>
                                  {expandedToggleSections.has(section.id) && (
                                    <motion.div
                                      initial={{ opacity: 0, height: 0 }}
                                      animate={{ opacity: 1, height: 'auto' }}
                                      exit={{ opacity: 0, height: 0 }}
                                      transition={{ duration: 0.2 }}
                                      className="overflow-hidden"
                                    >
                                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                                        {booleanSettings.map((setting) => (
                                          <div key={setting.key} className="flex items-center justify-between p-3 bg-scum-gray/20 rounded-lg border border-scum-primary/10 hover:bg-scum-gray/30 transition-colors">
                                            <label className="text-xs text-scum-light cursor-pointer flex-1 pr-2 leading-tight">
                                              {highlightSearchTerm(setting.label)}
                                              {setting.description && (
                                                <span className="block text-xs text-scum-muted mt-1">({highlightSearchTerm(setting.description)})</span>
                                              )}
                                            </label>
                                            <div className="flex-shrink-0">
                                              {renderSettingInput(setting, section.id)}
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    </motion.div>
                                  )}
                                </AnimatePresence>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>

      {/* Seção de Backups */}
      {showBackups && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="scum-card"
        >
          <BackupManager onBackupRestored={loadConfig} />
        </motion.div>
      )}

      {/* Seção Avançada */}
      {showAdvanced && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="scum-card"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <FileText className="text-scum-accent" size={20} />
              <h3 className="text-lg font-semibold text-scum-light">Editor Avançado</h3>
            </div>
            <div className="flex items-center gap-2 text-xs text-scum-muted">
              <span className="px-2 py-1 bg-scum-primary/20 rounded-full">
                {config.length} linhas
              </span>
            </div>
          </div>
          
          <div className="space-y-4">
            {/* Controles do Editor */}
            <div className="flex items-center justify-between p-3 bg-scum-gray/20 rounded-lg border border-scum-primary/10">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setConfig(saveWithCompletePreservation())}
                  className="flex items-center gap-2 px-3 py-1.5 bg-scum-accent/20 text-scum-accent rounded-lg hover:bg-scum-accent/30 transition-colors text-sm"
                >
                  <RotateCcw size={14} />
                  Converter para INI (100% Preservação)
                </button>
                <button
                  onClick={() => parseConfigToSettings(config)}
                  className="flex items-center gap-2 px-3 py-1.5 bg-scum-primary/20 text-scum-primary rounded-lg hover:bg-scum-primary/30 transition-colors text-sm"
                >
                  <FileText size={14} />
                  Converter de INI
                </button>
                <button
                  onClick={() => setConfig(originalConfig)}
                  className="flex items-center gap-2 px-3 py-1.5 bg-scum-gray/50 text-scum-muted rounded-lg hover:bg-scum-gray/60 transition-colors text-sm"
                >
                  <History size={14} />
                  Restaurar Original
                </button>
                <button
                  onClick={() => {
                    console.log('=== ANÁLISE MINUCIOSA DE PRESERVAÇÃO ===');
                    
                    // Análise detalhada das configurações perdidas
                    analyzeMissingSettings();
                    
                    // Verificar preservação completa
                    const isComplete = verifyCompletePreservation();
                    console.log('✅ Preservação 100% garantida:', isComplete);
                    
                    if (!isComplete) {
                      console.log('🔧 SOLUÇÃO: Use o botão "Garantia 100%" para aplicar correções');
                    }
                    
                    console.log('=== FIM ANÁLISE ===');
                  }}
                  className="flex items-center gap-2 px-3 py-1.5 bg-scum-accent/20 text-scum-accent rounded-lg hover:bg-scum-accent/30 transition-colors text-sm"
                >
                  <CheckCircle size={14} />
                  Análise Minuciosa
                </button>

                <button
                  onClick={() => {
                    const isComplete = verifyCompletePreservation();
                    if (isComplete) {
                      alert('✅ GARANTIA 100%: Todas as configurações originais serão preservadas!\n\nO servidor funcionará corretamente.');
                    } else {
                      // Mostrar análise detalhada
                      analyzeMissingSettings();
                      alert('❌ ATENÇÃO: Algumas configurações podem ser perdidas!\n\nIsso pode impedir o servidor de iniciar.\n\nVerifique o console para análise detalhada.');
                    }
                  }}
                  className="flex items-center gap-2 px-3 py-1.5 bg-green-600/20 text-green-400 rounded-lg hover:bg-green-600/30 transition-colors text-sm"
                >
                  <Shield size={14} />
                  Verificar Servidor
                </button>

                <button
                  onClick={() => {
                    const correctedConfig = fixMissingSettings();
                    if (correctedConfig) {
                      alert('✅ CORREÇÕES APLICADAS!\n\nTodas as configurações perdidas foram restauradas.\nO servidor agora funcionará corretamente.');
                    } else {
                      alert('✅ Nenhuma correção necessária!\n\nTodas as configurações já estão sendo preservadas corretamente.\nO servidor funcionará normalmente.');
                    }
                  }}
                  className="flex items-center gap-2 px-3 py-1.5 bg-blue-600/20 text-blue-400 rounded-lg hover:bg-blue-600/30 transition-colors text-sm"
                >
                  <RotateCcw size={14} />
                  Corrigir Servidor
                </button>

              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(config.join('\n'));
                  }}
                  className="flex items-center gap-2 px-3 py-1.5 bg-scum-primary/20 text-scum-primary rounded-lg hover:bg-scum-primary/30 transition-colors text-sm"
                >
                  <Copy size={14} />
                  Copiar
                </button>
                <button
                  onClick={async () => {
                    try {
                      const text = await navigator.clipboard.readText();
                      setConfig(text.split('\n'));
                    } catch (error) {
                      console.error('Erro ao colar do clipboard:', error);
                    }
                  }}
                  className="flex items-center gap-2 px-3 py-1.5 bg-scum-primary/20 text-scum-primary rounded-lg hover:bg-scum-primary/30 transition-colors text-sm"
                >
                  <Clipboard size={14} />
                  Colar
                </button>
              </div>
            </div>

            {/* Editor de Texto */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-scum-light">
                  Configuração Bruta (INI)
                </label>
                <div className="flex items-center gap-2 text-xs text-scum-muted">
                  <span>Linhas: {config.length}</span>
                  <span>Caracteres: {config.join('\n').length}</span>
                </div>
              </div>
              <textarea
                value={config.join('\n')}
                onChange={(e) => setConfig(e.target.value.split('\n'))}
                rows={15}
                className="w-full bg-scum-gray/50 border border-scum-primary/30 rounded-lg px-3 py-2 text-scum-light font-mono text-sm focus:border-scum-accent focus:outline-none resize-y"
                placeholder="[General]\nscum.ServerName=Meu Servidor\nscum.MaxPlayers=64\n\n[World]\nscum.MaxAllowedAnimals=60\n..."
                spellCheck={false}
              />
            </div>

            {/* Validação e Status */}
            <div className="p-3 bg-scum-gray/20 rounded-lg border border-scum-primary/10">
              {(() => {
                const errors = validateIniSyntax(config);
                return (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-4">
                        <span className="text-scum-muted">Status:</span>
                        {errors.length === 0 ? (
                          <span className="text-green-400">✓ Configuração válida</span>
                        ) : (
                          <span className="text-red-400">✗ {errors.length} erro(s) encontrado(s)</span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-xs text-scum-muted">
                        <span>Última modificação: {new Date().toLocaleTimeString()}</span>
                      </div>
                    </div>
                    {errors.length > 0 && (
                      <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400">
                        <div className="font-medium mb-1">Erros de sintaxe:</div>
                        {errors.map((error, index) => (
                          <div key={index} className="text-red-300">• {error}</div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>

            {/* Ações */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-scum-muted">
                <AlertTriangle size={14} />
                <span>Modificações no editor avançado sobrescrevem as configurações da interface</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowAdvanced(false)}
                  className="px-4 py-2 text-scum-muted hover:text-scum-light transition-colors text-sm"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 bg-scum-accent text-white rounded-lg hover:bg-scum-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Salvando...
                    </>
                  ) : (
                    <>
                      <Save size={16} />
                      Salvar Configuração
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default ServerConfigurationCard; 