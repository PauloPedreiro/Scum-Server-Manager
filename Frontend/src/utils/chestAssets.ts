const chestImageMap: Record<string, string> = {};

const modules = import.meta.glob('/src/assets/Baus/*.png', { eager: true, query: '?url', import: 'default' });

for (const [path, url] of Object.entries(modules)) {
  const fileName = path.split('/').pop();
  if (!fileName) continue;

  const baseName = fileName.replace('.png', '');
  chestImageMap[baseName.toLowerCase()] = url as string;
}

export function getChestThumbnail(chestClass: string | null | undefined, chestType: string | null | undefined): string | null {
  if (!chestClass && !chestType) {
    return null;
  }

  if (chestClass) {
    const key = chestClass.toLowerCase();
    if (chestImageMap[key]) {
      return chestImageMap[key];
    }
  }

  if (chestType) {
    const typeKey = `${chestType.toLowerCase()}_chest_es`;
    if (chestImageMap[typeKey]) {
      return chestImageMap[typeKey];
    }

    if (chestImageMap[chestType.toLowerCase()]) {
      return chestImageMap[chestType.toLowerCase()];
    }
  }

  return null;
}


