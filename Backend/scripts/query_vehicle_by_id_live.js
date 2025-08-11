const { getVehicleInfoLive } = require('./vehicle_database_query');

const id = process.argv[2];
if (!id) {
  console.log('Uso: node scripts/query_vehicle_by_id_live.js <VEHICLE_ID>');
  process.exit(1);
}

(async () => {
  try {
    const info = await getVehicleInfoLive(id);
    console.log(JSON.stringify(info, null, 2));
  } catch (e) {
    console.error('Erro:', e.message);
    process.exit(1);
  }
})();

