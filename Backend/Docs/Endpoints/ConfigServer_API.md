# ConfigServer API - Documentação para Frontend

## Visão Geral
API para gerenciar arquivos de configuração do servidor SCUM localizados em `C:/Servers/scum/SCUM/Saved/Config/WindowsServer`.

## Base URL
```
http://localhost:3000/api/configserver
```

---

## Endpoints Disponíveis

### 1. GET /ServerSettings.ini
**Ler o arquivo ServerSettings.ini completo**

**URL:** `GET http://localhost:3000/api/configserver/ServerSettings.ini`

**Resposta de Sucesso:**
```json
{
    "success": true,
    "content": [
        "[General]",
        "scum.ServerName=BLUE SECTOR BRASIL PVE [LOOT 3X SKILL 4X]",
        "scum.ServerDescription=BLUE SECTOR BRASIL PVE[LOOT 3X SKILL 4X]",
        "scum.ServerPassword=",
        "scum.MaxPlayers=64",
        "scum.ServerBannerUrl=https:",
        "scum.ServerPlaystyle=PVE",
        "scum.WelcomeMessage=Seja Bem-Vindo ao Melhor Servidor PVE discord.gg/thGphdRYJv",
        "scum.MessageOfTheDay=Servidor PVE Leia as Regras discord.gg/thGphdRYJv, Reset  01:00 05:00 09:00 13:00 17:00 21:00",
        "scum.MessageOfTheDayCooldown=10.000000",
        "scum.MinServerTickRate=10",
        "scum.MaxServerTickRate=40",
        "scum.MaxPing=300.000000",
        "scum.LogoutTimer=10.000000",
        "scum.LogoutTimerWhileCaptured=120.000000",
        "scum.LogoutTimerInBunker=30000.000000",
        "scum.AllowFirstPerson=1",
        "scum.AllowThirdPerson=1",
        "scum.AllowCrosshair=1",
        "scum.AllowVoting=1",
        "scum.AllowMapScreen=1",
        "scum.AllowKillClaiming=1",
        "scum.AllowComa=1",
        "scum.AllowMinesAndTraps=1",
        "scum.AllowSkillGainInSafeZones=1",
        "scum.AllowEvents=1",
        "scum.LimitGlobalChat=0",
        "scum.AllowGlobalChat=1",
        "scum.AllowLocalChat=1",
        "scum.AllowSquadChat=1",
        "scum.AllowAdminChat=1",
        "scum.RustyLocksLogging=1",
        "scum.HideKillNotification=0",
        "scum.DisableTimedGifts=0",
        "scum.UseMapBaseBuildingRestriction=1",
        "scum.DisableBaseBuilding=0",
        "scum.VotingDuration=60.000000",
        "scum.PlayerMinimalVotingInterest=0.500000",
        "scum.PlayerPositiveVotePercentage=0.500000",
        "scum.MasterServerEndpoints=",
        "scum.MasterServerUpdateSendInterval=60.000000",
        "scum.PartialWipe=0",
        "scum.GoldWipe=0",
        "scum.FullWipe=0",
        "scum.ItemVirtualizationRelevancyUpdatePeriod=1.000000",
        "scum.ItemVirtualizationEventProcessingTimeBudget=5.000000",
        "scum.ItemVirtualizationVisitorDistanceTravelledForUpdate=100.000000",
        "scum.ItemVirtualizationVisitorBounds=10000.000000",
        "scum.VirtualizedItemBounds=100.000000",
        "scum.FameGainMultiplier=2.500000",
        "scum.FamePointPenaltyOnDeath=0.100000",
        "scum.FamePointPenaltyOnKilled=0.250000",
        "scum.FamePointRewardOnKill=0.500000",
        "scum.LogSuicides=1",
        "scum.EnableSpawnOnGround=0",
        "scum.DeleteInactiveUsers=1",
        "scum.DaysSinceLastLoginToBecomeInactive=180",
        "scum.DeleteBannedUsers=0",
        "scum.MaximumTimeForChestsInForbiddenZones=24:00:00",
        "scum.LogChestOwnership=1",
        "scum.SettingsVersion=3",
        "scum.MasterServerIsLocalTest=0",
        "[World]",
        "scum.MaxAllowedBirds=10",
        "scum.MaxAllowedCharacters=220",
        "scum.MaxAllowedPuppets=-1",
        "scum.MaxAllowedAnimals=60",
        "scum.MaxAllowedNPCs=-1",
        "scum.EncounterBaseCharacterAmountMultiplier=1.000000",
        "scum.EncounterExtraCharacterPerPlayerMultiplier=1.000000",
        "scum.EncounterExtraCharacterPlayerCapMultiplier=1.000000",
        "scum.EncounterCharacterRespawnTimeMultiplier=1.000000",
        "scum.EncounterCharacterRespawnBatchSizeMultiplier=1.000000",
        "scum.EncounterCharacterAggressiveSpawnChanceOverride=-1.000000",
        "scum.EncounterCharacterAINoiseResponseRadiusMultiplier=1.000000",
        "scum.EncounterHordeGroupBaseCharacterAmountMultiplier=1.000000",
        "scum.EncounterHordeGroupExtraCharacterPerPlayerMultiplier=1.000000",
        "scum.EncounterHordeGroupExtraCharacterPlayerCapMultiplier=1.000000",
        "scum.EncounterHordeBaseCharacterAmountMultiplier=1.000000",
        "scum.EncounterHordeExtraCharacterPerPlayerMultiplier=1.000000",
        "scum.EncounterHordeExtraCharacterPlayerCapMultiplier=1.000000",
        "scum.EncounterHordeActivationChanceMultiplier=1.000000",
        "scum.EncounterHordeNoiseCheckCooldownMultiplier=1.000000",
        "scum.EncounterHordeSpawnDistanceMultiplier=1.000000",
        "scum.EncounterHordeGroupRefillTimeMultiplier=1.000000",
        "scum.EncounterHordeShouldPlayActivationSound=0",
        "scum.EncounterHordePuppetHordeActivationScreamOverrideChance=-1.000000",
        "scum.EncounterCanRemoveLowPriorityCharacters=1",
        "scum.EncounterCanClampCharacterNumWhenOutOfResources=1",
        "scum.EncounterGlobalZoneCooldownMultiplier=1.000000",
        "scum.EncounterEnableSpawnPreventionAreaSpawnOnCharacterDeath=1",
        "scum.PuppetWorldEncounterSpawnWeightMultiplier=1.000000",
        "scum.AnimalWorldEncounterSpawnWeightMultiplier=1.000000",
        "scum.DropshipWorldEncounterSpawnWeightMultiplier=1.000000",
        "scum.PawnSpawning.CheckOceanSpawnPoints=1",
        "scum.EnableDropshipAbandonedBunkerEncounter=1",
        "scum.DropshipAbandonedBunkerEncounterTriggerChance=-1.000000",
        "scum.BaseBuildingEncounterTriggerChance=-1.000000",
        "scum.BaseBuildingEncounterTriggerTimeMultiplier=1.000000",
        "scum.EnableDropshipBaseBuildingEncounter=0",
        "scum.SpawnEncountersInThreatZonesIgnoringBaseBuilding=0",
        "scum.EnableEncounterManagerLowPlayerCountMode=0",
        "scum.BaseBuildingEncounterMinNumElementsToStart=-1",
        "scum.BaseBuildingEncounterMinNumElementsToEnd=-1",
        "scum.BaseBuildingEncounterDamagePercentageIncreasePerSquadMember=0.000000",
        "scum.BaseBuildingEncounterTimeToFullMinNumToEnd=-1.000000",
        "scum.BaseBuildingEncounterMaximumMinToEndReduction=-1",
        "scum.MaxAllowedDrones=0",
        "scum.DisableSentrySpawning=0",
        "scum.EnableSentryRespawning=1",
        "scum.DisableSuicidePuppetSpawning=0",
        "scum.AbandonedBunkerCommotionThreshold=-1.000000",
        "scum.AbandonedBunkerCommotionThresholdPerPlayerExtra=-1.000000",
        "scum.AbandonedBunkerEnemyActivationThreshold=-1.000000",
        "scum.AbandonedBunkerEnemyActivationThresholdPerPlayerExtra=-1.000000",
        "scum.AbandonedBunkerResetArmoryLockersOnActivationOnly=1",
        "scum.PuppetsCanOpenDoors=1",
        "scum.PuppetsCanVaultWindows=1",
        "scum.PuppetHealthMultiplier=1.000000",
        "scum.DropshipHealthMultiplier=0.500000",
        "scum.SentryHealthMultiplier=1.000000",
        "scum.BaseBuildingAttackerSentryHealthMultiplier=0.500000",
        "scum.ArmedNPCDifficultyLevel=2",
        "scum.ProbabilityForArmedNPCToDropItemFromHandsWhenSearched=0.900000",
        "scum.StartTimeOfDay=06:00:00",
        "scum.TimeOfDaySpeed=9.000000",
        "scum.NighttimeDarkness=-0.300000",
        "scum.SunriseTime=05:00:00",
        "scum.SunsetTime=23:00:00",
        "scum.WeatherRainFrequencyMultiplier=0.02",
        "scum.WeatherRainDurationMultiplier=0.01",
        "scum.ShouldDestroyEntitiesOutsideMapLimitsOnRestart=0",
        "scum.EnableLockedLootContainers=1",
        "scum.CustomMapEnabled=0",
        "scum.CustomMapCenterXCoordinate=0.000000",
        "scum.CustomMapCenterYCoordinate=0.000000",
        "scum.CustomMapWidth=15.240000",
        "scum.CustomMapHeight=15.240000",
        "scum.DoorLockability.Garage=0",
        "scum.CargoDropCooldownMinimum=30.000000",
        "scum.CargoDropCooldownMaximum=30.000000",
        "scum.CargoDropFallDelay=180.000000",
        "scum.CargoDropFallDuration=180.000000",
        "scum.CargoDropSelfdestructTime=900.000000",
        "scum.CargoDropZombieEncounterWeightMultiplier=1.000000",
        "scum.CargoDropDropshipEncounterWeightMultiplier=1.000000",
        "scum.MaxAllowedHunts=25",
        "scum.HuntTriggerChanceOverride_ContinentalForest=-1.000000",
        "scum.HuntTriggerChanceOverride_ContinentalMeadow=-1.000000",
        "scum.HuntTriggerChanceOverride_Mediterranean=-1.000000",
        "scum.HuntTriggerChanceOverride_Mountain=-1.000000",
        "scum.HuntTriggerChanceOverride_Urban=-0.000000",
        "scum.HuntTriggerChanceOverride_Village=-0.000000",
        "scum.HuntFailureTime=150.000000",
        "scum.HuntFailureDistance=300.000000",
        "scum.BearMaxHealthMultiplier=1.000000",
        "scum.BoarMaxHealthMultiplier=1.000000",
        "scum.ChickenMaxHealthMultiplier=1.000000",
        "scum.DeerMaxHealthMultiplier=1.000000",
        "scum.DonkeyMaxHealthMultiplier=1.000000",
        "scum.GoatMaxHealthMultiplier=1.000000",
        "scum.HorseMaxHealthMultiplier=1.000000",
        "scum.RabbitMaxHealthMultiplier=1.000000",
        "scum.WolfMaxHealthMultiplier=1.000000",
        "scum.MaxAllowedKillboxKeycards=2",
        "scum.MaxAllowedKillboxKeycards_PoliceStation=2",
        "scum.MaxAllowedKillboxKeycards_RadiationZone=2",
        "scum.AbandonedBunkerMaxSimultaneouslyActive=2",
        "scum.AbandonedBunkerActiveDurationHours=24.000000",
        "scum.AbandonedBunkerKeyCardActiveDurationHours=3.000000",
        "scum.SecretBunkerKeyCardActiveDurationHours=1.000000",
        "scum.EncounterNeverRespawnCharacters=0",
        "scum.NPCWorldEncounterSpawnWeightMultiplier=1.000000",
        "[Respawn]",
        "scum.AllowSectorRespawn=1",
        "scum.AllowShelterRespawn=1",
        "scum.AllowSquadmateRespawn=1",
        "scum.RandomRespawnPrice=0",
        "scum.SectorRespawnPrice=200",
        "scum.ShelterRespawnPrice=500",
        "scum.SquadRespawnPrice=3000",
        "scum.RandomRespawnInitialTime=0.000000",
        "scum.SectorRespawnInitialTime=30.000000",
        "scum.ShelterRespawnInitialTime=30.000000",
        "scum.SquadRespawnInitialTime=60.000000",
        "scum.RandomRespawnCooldown=0.000000",
        "scum.SectorRespawnCooldown=30.000000",
        "scum.ShelterRespawnCooldown=30.000000",
        "scum.SquadRespawnCooldown=60.000000",
        "scum.RandomCooldownResetMultiplier=0.000000",
        "scum.SectorCooldownResetMultiplier=3.000000",
        "scum.ShelterCooldownResetMultiplier=3.000000",
        "scum.SquadCooldownResetMultiplier=2.000000",
        "scum.RandomPricePerSquadmateModifier=0.000000",
        "scum.SectorPricePerSquadmateModifier=0.000000",
        "scum.ShelterPricePerSquadmateModifier=0.000000",
        "scum.CommitSuicideInitialTime=0.000000",
        "scum.CommitSuicideCooldown=60.000000",
        "scum.CommitSuicideCooldownResetMultiplier=1.000000",
        "scum.MaximumBaseProximityWhenSpawning=10000.000000",
        "scum.PermadeathThreshold=-2500",
        "[Vehicles]",
        "scum.FuelDrainFromEngineMultiplier=0.800000",
        "scum.BatteryDrainFromEngineMultiplier=0.000000",
        "scum.BatteryDrainFromDevicesMultiplier=0.800000",
        "scum.BatteryDrainFromInactivityMultiplier=0.000000",
        "scum.BatteryChargeWithAlternatorMultiplier=1.000000",
        "scum.BatteryChargeWithDynamoMultiplier=1.000000",
        "scum.KingletDusterMaxAmount=15",
        "scum.KingletDusterMaxFunctionalAmount=20",
        "scum.KingletDusterMinPurchasedAmount=0",
        "scum.DirtbikeMaxAmount=15",
        "scum.DirtbikeMaxFunctionalAmount=25",
        "scum.DirtbikeMinPurchasedAmount=10",
        "scum.LaikaMaxAmount=30",
        "scum.LaikaMaxFunctionalAmount=50",
        "scum.LaikaMinPurchasedAmount=20",
        "scum.MotorboatMaxAmount=8",
        "scum.MotorboatMaxFunctionalAmount=12",
        "scum.MotorboatMinPurchasedAmount=10",
        "scum.WheelbarrowMaxAmount=0",
        "scum.WheelbarrowMaxFunctionalAmount=0",
        "scum.WheelbarrowMinPurchasedAmount=0",
        "scum.WolfswagenMaxAmount=20",
        "scum.WolfswagenMaxFunctionalAmount=40",
        "scum.WolfswagenMinPurchasedAmount=20",
        "scum.BicycleMaxAmount=10",
        "scum.BicycleMaxFunctionalAmount=0",
        "scum.BicycleMinPurchasedAmount=10",
        "scum.RagerMaxAmount=40",
        "scum.RagerMaxFunctionalAmount=60",
        "scum.RagerMinPurchasedAmount=20",
        "scum.CruiserMaxAmount=15",
        "scum.CruiserMaxFunctionalAmount=25",
        "scum.CruiserMinPurchasedAmount=10",
        "scum.RisMaxAmount=15",
        "scum.RisMaxFunctionalAmount=25",
        "scum.RisMinPurchasedAmount=10",
        "scum.SUPMaxAmount=0",
        "scum.SUPMaxFunctionalAmount=0",
        "scum.SUPMinPurchasedAmount=0",
        "scum.KingletMarinerMaxAmount=10",
        "scum.KingletMarinerMaxFunctionalAmount=15",
        "scum.KingletMarinerMinPurchasedAmount=0",
        "scum.TractorMaxAmount=15",
        "scum.TractorMaxFunctionalAmount=25",
        "scum.TractorMinPurchasedAmount=10",
        "scum.MaximumTimeOfVehicleInactivity=168:00:00",
        "scum.MaximumTimeForVehiclesInForbiddenZones=02:00:00",
        "scum.LogVehicleDestroyed=1",
        "scum.EnableVehicleDamage=1",
        "scum.VehicleDecayTime=1.000000",
        "scum.HumanToVehicleDamageMultiplier=0.0",
        "scum.ZombieToVehicleDamageMultiplier=0.0",
        "[Damage]",
        "scum.HumanToHumanDamageMultiplier=1.000000",
        "scum.HumanToHumanArmedMeleeDamageMultiplier=1.000000",
        "scum.HumanToHumanUnarmedMeleeDamageMultiplier=1.000000",
        "scum.HumanToHumanThrowingDamageMultiplier=1.000000",
        "scum.ShowKillFeed=True",
        "scum.SentryDamageMultiplier=0.800000",
        "scum.SentryRailgunDamageMultiplier=0.800000",
        "scum.SentryGrenadeDamageMultiplier=0.800000",
        "scum.BaseBuildingAttackerSentryDamageMultiplier=0.000000",
        "scum.BaseBuildingAttackerSentryRailgunDamageMultiplier=0.000000",
        "scum.BaseBuildingAttackerSentryGrenadeDamageMultiplier=0.000000",
        "scum.SentryBaseBuildingDamageMultiplier=0.000000",
        "scum.DropshipDamageMultiplier=0.500000",
        "scum.DropshipRailgunDamageMultiplier=0.500000",
        "scum.DropshipBaseBuildingElementsDamageMultiplier=0.000000",
        "scum.ZombieDamageMultiplier=2.000000",
        "scum.ItemDecayDamageMultiplier=0.500000",
        "scum.FoodDecayDamageMultiplier=0.500000",
        "scum.WeaponDecayDamageOnFiring=0.500000",
        "scum.LockProtectionDamageMultiplier=1.000000",
        "[Features]",
        "scum.FlagOvertakeDuration=24:00:00",
        "scum.MaximumAmountOfElementsPerFlag=1000",
        "scum.ExtraElementsPerFlagForAdditionalSquadMember=25",
        "scum.MaximumNumberOfExpandedElementsPerFlag=100",
        "scum.AllowMultipleFlagsPerPlayer=1",
        "scum.AllowFlagPlacementOnBBElements=0",
        "scum.ChestAcquisitionDuration=64.000000",
        "scum.WeaponRackMaxAmountPerFlagArea=7",
        "scum.WeaponRackStartDecayingIfFlagAreaHasMoreThan=9",
        "scum.WallWeaponRackMaxAmountPerFlagArea=7",
        "scum.WallWeaponRackStartDecayingIfFlagAreaHasMoreThan=9",
        "scum.WellMaxAmountPerFlagArea=2",
        "scum.WellStartDecayingIfFlagAreaHasMoreThan=4",
        "scum.TurretMaxAmountPerFlagArea=2",
        "scum.TurretStartDecayingIfFlagAreaHasMoreThan=3",
        "scum.GardenMaxAmountPerFlagArea=2",
        "scum.AllowFloorPlacementOnHalfAndLowWalls=1",
        "scum.AllowWallPlacementOnHalfAndLowWalls=1",
        "scum.RaidProtectionType=0",
        "scum.RaidProtectionEnableLog=0",
        "scum.RaidProtectionFlagSpecificChangeSettingCooldown=120:00:00",
        "scum.RaidProtectionFlagSpecificChangeSettingPrice=10g",
        "scum.RaidProtectionFlagSpecificMaxProtectionTime=08:00:00",
        "scum.RaidProtectionOfflineProtectionStartDelay=00:30:00",
        "scum.RaidProtectionOfflineMaxProtectionTime=-",
        "scum.RaidProtectionGlobalShouldShowRaidTimesMessage=1",
        "scum.RaidProtectionGlobalShouldShowRaidAnnouncementMessage=1",
        "scum.RaidProtectionGlobalShouldShowRaidStartEndMessages=1",
        "scum.WaterPricePerUnitMultiplier=1.000000",
        "scum.WaterPeriodicInitialAmountMultiplier=2.000000",
        "scum.WaterPeriodicMaxAmountMultiplier=3.000000",
        "scum.WaterPeriodicReplenishAmountMultiplier=3.000000",
        "scum.WaterPeriodicReplenishIntervalMultiplier=0.500000",
        "scum.WaterProximityReplenishAmountMultiplier=3.000000",
        "scum.WaterProximityReplenishChanceMultiplier=3.000000",
        "scum.WaterProximityReplenishTimeoutMultiplier=0.500000",
        "scum.GasolinePricePerUnitMultiplier=1.000000",
        "scum.GasolinePeriodicInitialAmountMultiplier=1.000000",
        "scum.GasolinePeriodicInitialAmountMultiplier=1.000000",
        "scum.GasolinePeriodicMaxAmountMultiplier=2.000000",
        "scum.GasolinePeriodicReplenishAmountMultiplier=2.000000",
        "scum.GasolinePeriodicReplenishIntervalMultiplier=0.500000",
        "scum.GasolineProximityReplenishAmountMultiplier=2.000000",
        "scum.GasolineProximityReplenishChanceMultiplier=2.000000",
        "scum.GasolineProximityReplenishTimeoutMultiplier=0.500000",
        "scum.PropanePricePerUnitMultiplier=1.000000",
        "scum.PropanePeriodicInitialAmountMultiplier=1.000000",
        "scum.PropanePeriodicMaxAmountMultiplier=1.000000",
        "scum.PropanePeriodicReplenishAmountMultiplier=1.000000",
        "scum.PropanePeriodicReplenishIntervalMultiplier=1.000000",
        "scum.PropaneProximityReplenishAmountMultiplier=1.000000",
        "scum.PropaneProximityReplenishChanceMultiplier=1.000000",
        "scum.PropaneProximityReplenishTimeoutMultiplier=1.000000",
        "scum.SpawnerProbabilityMultiplier=3.000000",
        "scum.ExamineSpawnerProbabilityMultiplier=3.000000",
        "scum.ExamineSpawnerExpirationTimeMultiplier=0.500000",
        "scum.SpawnerExpirationTimeMultiplier=0.500000",
        "scum.EnableItemCooldownGroups=1",
        "scum.ItemCooldownGroupsDurationMultiplier=1.000000",
        "scum.SquadMemberCountAtIntLevel1=2",
        "scum.SquadMemberCountAtIntLevel2=4",
        "scum.SquadMemberCountAtIntLevel3=6",
        "scum.SquadMemberCountAtIntLevel4=8",
        "scum.SquadMemberCountAtIntLevel5=10",
        "scum.SquadMemberCountLimitForPunishment=2",
        "scum.RTSquadProbationDuration=0.000000",
        "scum.SquadMoneyPenaltyPerPrevSquadMember=0",
        "scum.SquadFamePointsPenaltyPerPrevSquadMember=0",
        "scum.EnableSquadMemberNameWidget=1",
        "scum.PlantHarvestExamineTimeMultiplier=0.500000",
        "scum.FirstPlantHarvestAdditionalChance=1.000000",
        "scum.ArcherySkillMultiplier=4.000000",
        "scum.AviationSkillMultiplier=4.000000",
        "scum.AwarenessSkillMultiplier=4.000000",
        "scum.BrawlingSkillMultiplier=4.000000",
        "scum.CamouflageSkillMultiplier=4.000000",
        "scum.CookingSkillMultiplier=4.000000",
        "scum.DemolitionSkillMultiplier=4.000000",
        "scum.DrivingSkillMultiplier=4.000000",
        "scum.EnduranceSkillMultiplier=4.000000",
        "scum.EngineeringSkillMultiplier=4.000000",
        "scum.FarmingSkillMultiplier=4.000000",
        "scum.HandgunSkillMultiplier=4.000000",
        "scum.MedicalSkillMultiplier=4.000000",
        "scum.MeleeWeaponsSkillMultiplier=4.000000",
        "scum.MotorcycleSkillMultiplier=4.000000",
        "scum.RiflesSkillMultiplier=4.000000",
        "scum.RunningSkillMultiplier=4.000000",
        "scum.SnipingSkillMultiplier=4.000000",
        "scum.StealthSkillMultiplier=4.000000",
        "scum.SurvivalSkillMultiplier=4.000000",
        "scum.ThieverySkillMultiplier=4.000000",
        "scum.QuestsEnabled=1",
        "scum.QuestsGlobalCycleDuration=12:00:00",
        "scum.MaxQuestsPerCyclePerTrader=3",
        "scum.MaxSimultaneousQuestsPerTrader=1",
        "scum.QuestsTraderRefillCooldown=02:00:00",
        "scum.QuestsPhoneRefillCooldown=01:00:00",
        "scum.QuestsNoticeBoardRefillCooldown=02:00:00",
        "scum.QuestRequirementsBlockTradeableItems=0",
        "scum.TurretsAttackPrisoners=0",
        "scum.TurretsAttackPuppets=1",
        "scum.TurretsAttackVehicles=0",
        "scum.TurretsAttackSentries=1",
        "scum.TurretsAttackAnimals=0",
        "scum.TurretsAttackArmedNPCs=1",
        "scum.MovementInertiaAmount=1.000000",
        "scum.StaminaDrainOnJumpMultiplier=0.250000",
        "scum.StaminaDrainOnClimbMultiplier=0.250000",
        "scum.DisableExhaustion=1",
        "scum.BodySimulationSpeedMultiplier=2.500000",
        "scum.MaintainItemsExpirationTime=72:00:00",
        "scum.KillboxDefuseFailureBonus=0.300000",
        "scum.BedrollVisibilityTimer=1.000000",
        "scum.EnableBCULocking=1",
        "scum.NameChangeCooldown=168.000000",
        "scum.NameChangeCost=500",
        "scum.EnableNewPlayerProtection=1",
        "scum.NewPlayerProtectionDuration=120.000000",
        "scum.AllowAutomaticParachuteOpening=1",
        "scum.HideQuickAccessBar=0",
        "scum.HideLifeIndicators=0",
        "scum.EnableDeenaOnServer=0",
        "scum.EnableDigitalDeluxeStarterPack=1",
        "scum.EnableNetWatchdog=0"
    ],
    "stats": {
        "size": 16610,
        "modified": "2025-07-21T00:00:52.813Z",
        "created": "2025-07-16T01:00:57.141Z"
    }
}
```

**Resposta de Erro:**
```json
{
    "success": false,
    "error": "Arquivo não encontrado"
}
```

---

### 2. PUT /ServerSettings.ini
**Atualizar arquivo ServerSettings.ini completo**

**URL:** `PUT http://localhost:3000/api/configserver/ServerSettings.ini`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
    "content": [
        "[General]",
        "scum.ServerName=MEU SERVIDOR SCUM BRASIL",
        "scum.ServerDescription=Descrição do meu servidor",
        "scum.MaxPlayers=128",
        "scum.FameGainMultiplier=3.000000",
        "[World]",
        "scum.MaxAllowedBirds=15",
        "scum.MaxAllowedCharacters=250",
        "[Vehicles]",
        "scum.KingletDusterMaxAmount=20",
        "scum.DirtbikeMaxAmount=25"
    ]
}
```

**Resposta de Sucesso:**
```json
{
    "success": true,
    "message": "Arquivo ServerSettings.ini atualizado com sucesso",
    "backupCreated": "ServerSettings_ini_2025-07-21_01-05-30.backup",
    "linesCount": 10
}
```

**Resposta de Erro:**
```json
{
    "success": false,
    "error": "Conteúdo deve ser um array de linhas"
}
```

**Resposta de Erro de Validação:**
```json
{
    "success": false,
    "error": "Formato INI inválido",
    "details": [
        "Linha 5: Chave vazia"
    ]
}
```

---

### 3. PUT /ServerSettings.ini/:section/:key
**Atualizar valor específico no ServerSettings.ini**

**URL:** `PUT http://localhost:3000/api/configserver/ServerSettings.ini/General/scum.ServerName`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
    "value": "NOVO NOME DO SERVIDOR"
}
```

**Resposta de Sucesso:**
```json
{
    "success": true,
    "message": "Valor atualizado: [General] scum.ServerName=NOVO NOME DO SERVIDOR",
    "backupCreated": "ServerSettings_ini_2025-07-21_01-10-45.backup",
    "updated": true
}
```

**Resposta de Erro:**
```json
{
    "success": false,
    "error": "Valor é obrigatório"
}
```

---

### 4. GET /backups
**Listar todos os backups disponíveis**

**URL:** `GET http://localhost:3000/api/configserver/backups`

**Resposta de Sucesso:**
```json
{
    "success": true,
    "backups": [
        {
            "filename": "ServerSettings_ini_2025-07-21_01-05-30.backup",
            "size": 16610,
            "created": "2025-07-21T01:05:30.000Z",
            "originalFile": "ServerSettings.ini"
        },
        {
            "filename": "ServerSettings_ini_2025-07-20_22-01-59.backup",
            "size": 16610,
            "created": "2025-07-20T22:01:59.000Z",
            "originalFile": "ServerSettings.ini"
        }
    ]
}
```

---

### 5. POST /backups/restore/:filename
**Restaurar backup específico**

**URL:** `POST http://localhost:3000/api/configserver/backups/restore/ServerSettings_ini_2025-07-21_01-05-30.backup`

**Resposta de Sucesso:**
```json
{
    "success": true,
    "message": "Backup restaurado com sucesso",
    "restoredFile": "ServerSettings_ini_2025-07-21_01-05-30.backup"
}
```

**Resposta de Erro:**
```json
{
    "success": false,
    "error": "Backup não encontrado"
}
```

---

### 6. GET /ServerSettings.ini/info
**Obter informações resumidas do arquivo**

**URL:** `GET http://localhost:3000/api/configserver/ServerSettings.ini/info`

**Resposta de Sucesso:**
```json
{
    "success": true,
    "info": {
        "sections": [
            "General",
            "World",
            "Respawn",
            "Vehicles",
            "Damage",
            "Features"
        ],
        "totalLines": 150,
        "size": 16610,
        "modified": "2025-07-21T00:00:52.813Z",
        "importantSettings": {
            "scum.ServerName": "BLUE SECTOR BRASIL PVE [LOOT 3X SKILL 4X]",
            "scum.ServerDescription": "BLUE SECTOR BRASIL PVE[LOOT 3X SKILL 4X]",
            "scum.MaxPlayers": "64",
            "scum.FameGainMultiplier": "2.500000",
            "scum.FamePointPenaltyOnDeath": "0.100000",
            "scum.FamePointPenaltyOnKilled": "0.250000",
            "scum.FamePointRewardOnKill": "0.500000"
        }
    }
}
```

---

## Características Importantes

### Formato de Dados
- **GET** retorna o conteúdo como **array de linhas** (não string)
- **PUT** espera receber o conteúdo como **array de linhas**
- Cada linha representa uma configuração ou seção
- Seções são identificadas por `[NomeSeção]`
- Configurações seguem o formato `chave=valor`

### Backup Automático
- **SEMPRE** é criado um backup antes de qualquer modificação
- Backups são salvos em `src/data/configserver/backups/`
- Nome do backup: `{arquivo}_{timestamp}.backup`
- Exemplo: `ServerSettings_ini_2025-07-21_01-05-30.backup`

### Validação
- O endpoint PUT completo valida o formato INI
- Aceita seções `[Nome]`
- Aceita configurações `chave=valor`
- Aceita linhas vazias e comentários `;`
- Rejeita chaves vazias

### Estrutura de Seções
O ServerSettings.ini contém as seguintes seções principais:
- `[General]` - Configurações gerais do servidor
- `[World]` - Configurações do mundo e NPCs
- `[Respawn]` - Configurações de respawn
- `[Vehicles]` - Configurações de veículos
- `[Damage]` - Configurações de dano
- `[Features]` - Recursos especiais

---

## Exemplos de Uso no Frontend

### JavaScript/TypeScript

```typescript
// Ler configuração atual
const getConfig = async () => {
    const response = await fetch('http://localhost:3000/api/configserver/ServerSettings.ini');
    const data = await response.json();
    return data.content; // Array de linhas
};

// Atualizar configuração completa
const updateConfig = async (lines: string[]) => {
    const response = await fetch('http://localhost:3000/api/configserver/ServerSettings.ini', {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content: lines })
    });
    return await response.json();
};

// Atualizar valor específico
const updateValue = async (section: string, key: string, value: string) => {
    const response = await fetch(`http://localhost:3000/api/configserver/ServerSettings.ini/${section}/${key}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ value })
    });
    return await response.json();
};

// Listar backups
const getBackups = async () => {
    const response = await fetch('http://localhost:3000/api/configserver/backups');
    return await response.json();
};

// Restaurar backup
const restoreBackup = async (filename: string) => {
    const response = await fetch(`http://localhost:3000/api/configserver/backups/restore/${filename}`, {
        method: 'POST'
    });
    return await response.json();
};
```

### React Hook Example

```typescript
import { useState, useEffect } from 'react';

interface ConfigData {
    success: boolean;
    content: string[];
    stats?: {
        size: number;
        modified: string;
        created: string;
    };
}

export const useServerConfig = () => {
    const [config, setConfig] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadConfig = async () => {
        setLoading(true);
        try {
            const response = await fetch('http://localhost:3000/api/configserver/ServerSettings.ini');
            const data: ConfigData = await response.json();
            
            if (data.success) {
                setConfig(data.content);
                setError(null);
            } else {
                setError(data.error);
            }
        } catch (err) {
            setError('Erro ao carregar configuração');
        } finally {
            setLoading(false);
        }
    };

    const saveConfig = async (newConfig: string[]) => {
        setLoading(true);
        try {
            const response = await fetch('http://localhost:3000/api/configserver/ServerSettings.ini', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content: newConfig })
            });
            
            const data = await response.json();
            
            if (data.success) {
                setConfig(newConfig);
                setError(null);
                return data;
            } else {
                setError(data.error);
                return data;
            }
        } catch (err) {
            setError('Erro ao salvar configuração');
            return { success: false, error: 'Erro ao salvar configuração' };
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadConfig();
    }, []);

    return {
        config,
        loading,
        error,
        loadConfig,
        saveConfig
    };
};
```

---

## Notas para o Desenvolvedor Frontend

1. **Sempre use o PUT completo** para atualizações - é mais seguro e flexível
2. **O frontend controla toda a organização** - seções, ordem, valores
3. **Backup automático** - não precisa se preocupar com isso
4. **Validação no backend** - o frontend pode focar na UX
5. **Array de linhas** - mais fácil de manipular no frontend
6. **Tratamento de erros** - sempre verifique `success` na resposta
7. **Loading states** - use para melhor UX durante operações
8. **Confirmação** - sempre confirme antes de salvar mudanças importantes

---

## Status Codes

- `200` - Sucesso
- `400` - Erro de validação ou dados inválidos
- `404` - Arquivo não encontrado
- `500` - Erro interno do servidor

---

## Logs e Monitoramento

O backend registra todas as operações nos logs:
- Leitura de arquivos
- Atualizações com backup
- Restaurações de backup
- Erros de validação
- Erros de sistema

Verifique os logs do servidor para debug quando necessário. 