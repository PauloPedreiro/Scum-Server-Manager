export interface ScumWikiCategory {
  id: string;
  listId: number;
  name: string;
  color: string;
}

export interface ScumWikiMarkerLink {
  url: string;
  label: string;
}

export interface ScumWikiMarkerPopup {
  title: string;
  description?: string;
  link?: ScumWikiMarkerLink;
}

export interface ScumWikiMarker {
  id: string;
  categoryId: string;
  position: [number, number];
  popup?: ScumWikiMarkerPopup;
}

export const SCUM_WIKI_MAP_BOUNDS: [[number, number], [number, number]] = [
  [0, 0],
  [903, 908],
];

export const SCUM_WIKI_ORIGIN: 'bottom-left' = 'bottom-left';

export const SCUM_WIKI_CATEGORIES: ScumWikiCategory[] = [
  { id: '1', listId: 1, name: 'General', color: '#f00' },
  { id: '2', listId: 2, name: 'Points of Interest', color: '#FA005A' },
  { id: '3', listId: 3, name: 'Bunkers', color: '#fa8e00' },
  { id: '4', listId: 4, name: 'Player Position', color: '#00fafa' },
  { id: '5', listId: 5, name: 'Base Locations', color: '#0cfa00' },
  { id: '6', listId: 6, name: 'Traders', color: '#0c00fa' },
];

export const SCUM_WIKI_MARKERS: ScumWikiMarker[] = [
  {
    id: '1',
    categoryId: '2',
    position: [520.5, 517],
    popup: {
      title: 'Airport',
      description: 'Unknown',
      link: { url: 'Airport', label: 'Airport' },
    },
  },
  {
    id: '2',
    categoryId: '2',
    position: [608, 533],
    popup: {
      title: 'Factory',
      description: 'Unknown',
      link: { url: 'Factory', label: 'Factory' },
    },
  },
  {
    id: '3',
    categoryId: '2',
    position: [876.75, 849.75],
    popup: {
      title: 'Military Barracks',
      description: 'Loot?',
      link: { url: 'Military_Barrack', label: 'Military Barracks' },
    },
  },
  {
    id: '4',
    categoryId: '3',
    position: [495.85863030707, 652.65955903518],
    popup: {
      title: 'C2 Bunker',
      description:
        'Bunker Layout\nLarge multi level complex, hallways covered in potential loot.\n\nStrategy\nApproach the bunker from the North side. Be warned, the sentry has an extremely short pattern, so you will have to move quickly.\n\nLoot\nOverall loot quality: 5/5 8 armories on upper level within four hallways.',
      link: { url: 'C2 Bunker', label: 'C2 Bunker' },
    },
  },
  {
    id: '5',
    categoryId: '3',
    position: [712.76363543604, 382.54476862192],
    popup: {
      title: 'B1 Bunker',
      description:
        'Bunker Layout\nBasically 2 crossing hallways with lab spaces as well as a couple of armories.\n\nStrategy\nEnter the camp from the west, approach the entrance from the south door of mess hall.\n\nLoot\nOverall Loot quality: 3/5',
      link: { url: 'B1 Bunker', label: 'B1 Bunker' },
    },
  },
  {
    id: '6',
    categoryId: '3',
    position: [223.44574285495, 482.77715485512],
    popup: {
      title: 'B3 Bunker',
      description:
        'Bunker Layout\nLarge mechanical space with good loot. Several armories.\n\nStrategy\nThis section is currently empty, You can help Scum Wiki by expanding it.\n\nLoot\nOverall loot quality: 4/5',
      link: { url: 'B3 Bunker', label: 'B3 Bunker' },
    },
  },
  {
    id: '7',
    categoryId: '1',
    position: [455.37676708414, 710.81909178778],
    popup: {
      title: 'C2 Outpost',
      description:
        'The first outpost you will find on the well known C2 island in the middle of the lake (RPI church island) This outpost is in the cold and can be approached from the air via its own airstrip, by water of course and it has 3 landmass approaches, a bridge and 2 shallow water ones.',
      link: { url: 'C2 Outpost', label: 'C2 Outpost' },
    },
  },
  {
    id: '8',
    categoryId: '2',
    position: [72.25, 879.25],
    popup: {
      title: 'Military Airfield',
      description: 'Self Explanatory',
      link: { url: 'Military Airfield', label: 'Military Airfield' },
    },
  },
  {
    id: '10',
    categoryId: '3',
    position: [881.05504935844, 645.58849122332],
    popup: {
      title: 'C0 Bunker',
      description: 'Unknown',
      link: { url: 'C0 Bunker', label: 'C0 Bunker' },
    },
  },
  {
    id: '11',
    categoryId: '3',
    position: [599.2729970556, 669.27656839307],
    popup: {
      title: 'C1 Bunker',
      description: 'Unknown',
      link: { url: 'C1 Bunker', label: 'C1 Bunker' },
    },
  },
  {
    id: '12',
    categoryId: '3',
    position: [100.40916292849, 695.43951929697],
    popup: {
      title: 'C4 Bunker',
      description: 'Unknown',
      link: { url: 'C4 Bunker', label: 'C4 Bunker' },
    },
  },
  {
    id: '14',
    categoryId: '3',
    position: [574.52425971407, 264.45793616377],
    popup: {
      title: 'A1 Bunker',
      description: 'Unknown',
      link: { url: 'A1 Bunker', label: 'A1 Bunker' },
    },
  },
  {
    id: '15',
    categoryId: '3',
    position: [391.03004999616, 344.00744904726],
    popup: {
      title: 'A2 Bunker',
      description: 'Unknown',
      link: { url: 'A2 Bunker', label: 'A2 Bunker' },
    },
  },
  {
    id: '16',
    categoryId: '3',
    position: [228.74904371385, 273.65032431919],
    popup: {
      title: 'A3 Bunker',
      description: 'Unknown',
      link: { url: 'A3 Bunker', label: 'A3 Bunker' },
    },
  },
  {
    id: '17',
    categoryId: '3',
    position: [98.641395975523, 300.87393539488],
    popup: {
      title: 'A4 Bunker',
      description: 'Unknown',
      link: { url: 'A4 Bunker', label: 'A4 Bunker' },
    },
  },
  {
    id: '18',
    categoryId: '3',
    position: [845.34615690852, 488.25723240931],
    popup: {
      title: 'B0 Bunker',
      description: 'Unknown',
      link: { url: 'B0 Bunker', label: 'B0 Bunker' },
    },
  },
  {
    id: '19',
    categoryId: '3',
    position: [391.38360338675, 422.84985514956],
    popup: {
      title: 'B2 Bunker',
      description: 'Unknown',
      link: { url: 'B2 Bunker', label: 'B2 Bunker' },
    },
  },
  {
    id: '20',
    categoryId: '3',
    position: [100.40916292849, 531.0371926711],
    popup: {
      title: 'B4 Bunker',
      description: 'Unknown',
      link: { url: 'B4 Bunker', label: 'B4 Bunker' },
    },
  },
  {
    id: '21',
    categoryId: '3',
    position: [252.75, 715],
    popup: {
      title: 'C3 Bunker',
      description: 'Unknown',
      link: { url: 'C3 Bunker', label: 'C3 Bunker' },
    },
  },
  {
    id: '22',
    categoryId: '3',
    position: [885.29769004556, 895.19718498217],
    popup: {
      title: 'D0 Bunker',
      description: 'Unknown',
      link: { url: 'D0 Bunker', label: 'D0 Bunker' },
    },
  },
  {
    id: '23',
    categoryId: '3',
    position: [686.5, 859],
    popup: {
      title: 'D1 Bunker',
      description: 'Unknown',
      link: { url: 'D1 Bunker', label: 'D1 Bunker' },
    },
  },
  {
    id: '24',
    categoryId: '3',
    position: [509.8239892355, 876.45885528073],
    popup: {
      title: 'D2 Bunker',
      description: 'Unknown',
      link: { url: 'D2 Bunker', label: 'D2 Bunker' },
    },
  },
  {
    id: '25',
    categoryId: '3',
    position: [281, 864.75],
    popup: {
      title: 'D3 Bunker',
      description: 'Unknown',
      link: { url: 'D3 Bunker', label: 'D3 Bunker' },
    },
  },
  {
    id: '26',
    categoryId: '3',
    position: [125.51145366061, 869.03423407827],
    popup: {
      title: 'D4 Bunker',
      description: 'Unknown',
      link: { url: 'D4 Bunker', label: 'D4 Bunker' },
    },
  },
  {
    id: '27',
    categoryId: '3',
    position: [779, 68.75],
    popup: {
      title: 'Z0 Bunker',
      description: 'Unknown',
      link: { url: 'Z0 Bunker', label: 'Z0 Bunker' },
    },
  },
  {
    id: '28',
    categoryId: '3',
    position: [704.25, 108.75],
    popup: {
      title: 'Z1 Bunker',
      description: 'Unknown',
      link: { url: 'Z1 Bunker', label: 'Z1 Bunker' },
    },
  },
  {
    id: '29',
    categoryId: '3',
    position: [486, 155.5],
    popup: {
      title: 'Z2 Bunker',
      description: 'Unknown',
      link: { url: 'Z2 Bunker', label: 'Z2 Bunker' },
    },
  },
  {
    id: '30',
    categoryId: '3',
    position: [345.25, 57.75],
    popup: {
      title: 'Z3 Bunker',
      description: 'Unknown',
      link: { url: 'Z3 Bunker', label: 'Z3 Bunker' },
    },
  },
  {
    id: '31',
    categoryId: '3',
    position: [54.25, 48.25],
    popup: {
      title: 'Z4 Bunker',
      description: 'Unknown',
      link: { url: 'Z4 Bunker', label: 'Z4 Bunker' },
    },
  },
  {
    id: '32',
    categoryId: '2',
    position: [216.75, 518.25],
    popup: {
      title: 'Boot Camp',
      description: 'Weapons & Ammo',
      link: { url: 'Boot Camp', label: 'Boot Camp' },
    },
  },
  {
    id: '33',
    categoryId: '5',
    position: [556, 541.5],
    popup: {
      title: 'Airport F.O.B.',
      description: '',
      link: { url: '', label: '' },
    },
  },
  {
    id: '34',
    categoryId: '6',
    position: [731.5, 212],
    popup: {
      title: 'A0 Trader',
      description: '',
      link: { url: 'A0 Trader', label: 'A0 Trader' },
    },
  },
  {
    id: '35',
    categoryId: '2',
    position: [150.61374439273462, 229.80970388562793],
    popup: {
      title: 'small airport',
      description: 'gas/',
      link: { url: '', label: '' },
    },
  },
  {
    id: '36',
    categoryId: '2',
    position: [164.5, 245],
    popup: {
      title: 'yy',
      description: 'grapes',
      link: { url: '', label: '' },
    },
  },
];
