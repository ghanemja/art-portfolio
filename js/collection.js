// ─── THE COLLECTION ─────────────────────────────────────────────────────────
// Everything the museum shows, in hanging order. Edit freely:
//   file    the image's name in artworks/ (full size: artworks/<file>.jpg; in-world: artworks/web/<file>.webp)
//   title, year, medium, note: shown on the wall card and in the viewer ('' hides a line)
//   w, h    the image's pixel size (only its shape matters: the frame is cut to fit)
//   shape   'oval' for a round canvas (it hangs in an oval frame)
//   group   paintings sharing a group hang together as a 2×2 collage (groupTitle names the set)
// To add a painting: put the photo in artworks/originals/<file>.jpg, add its row here, and run
// `python3 scripts/prep-art.py`: it crops away the backdrop, turns sideways ones upright (its
// ROTATE list), and fills in w, h and shape. The hall grows to fit.
export const ARTIST = {
  name: 'Janelle Ghanem',
  museum: 'THE GHANEM GALLERY OF ART',   // carved over the portico
  short: 'THE GHANEM GALLERY',           // on the banners
  tagline: 'paintings, hung in a museum that floats',
  links: [],                             // [['label', 'https://…'], …] shown on the name card
};

// the guided tour's stops, in order (by file name)
export const TOUR = ['art_IMG_0658', 'art_IMG_5264', 'art_IMG_5263', 'art_IMG_5261'];   // the horses, the castle, the ship, the harbour

export const WORKS = [
  { file: 'art_banana_treats_astronaut', title: 'Banana Treats for the Astronaut', year: '', medium: '', w: 701, h: 702 },
  { file: 'art_cows_in_storm', title: 'Cows in Storm', year: '', medium: '', w: 1110, h: 807 },
  { file: 'art_space_heist_mice', title: 'Space Heist Mice', year: '', medium: '', w: 698, h: 337 },
  { file: 'art_sunset_swell', title: 'Sunset Swell', year: '', medium: '', w: 717, h: 573 },
  { file: 'art_IMG_0471', title: 'Palm in a Pink Storm', year: '', medium: '', w: 1015, h: 806 },
  { file: 'art_IMG_0658', title: 'Wild Horses at the Falls', year: '', medium: '', w: 1110, h: 880 },
  { file: 'art_IMG_2256', title: 'Lavender Peaks Harbour', year: '', medium: '', w: 1110, h: 1084 },
  { file: 'art_IMG_5261', title: 'Harbour of Painted Houses', year: '', medium: '', w: 1110, h: 868 },
  { file: 'art_IMG_5262', title: 'Autumn River Pass', year: '', medium: '', w: 1110, h: 1425 },
  { file: 'art_IMG_5263', title: 'Storm Ship in Ink', year: '', medium: '', w: 1110, h: 806 },
  { file: 'art_IMG_5264', title: 'Castle Above the Valley', year: '', medium: '', w: 1110, h: 866 },
  { file: 'art_IMG_5265', title: 'Polar Bears at Dusk', year: '', medium: '', w: 1110, h: 861 },
  { file: 'art_IMG_5271', title: 'The Yellow House at Sundown', year: '', medium: '', w: 1110, h: 889 },
  { file: 'art_IMG_5557', title: 'Aurora Over the Sea', year: '', medium: '', w: 825, h: 825, shape: 'oval' },
  { file: 'art_IMG_7121', title: 'Pink Morning at the Lake', year: '', medium: '', w: 1019, h: 813 },
  { file: 'art_IMG_7135', title: 'Rowing into the Sunset', year: '', medium: '', w: 993, h: 783 },
  { file: 'art_IMG_7152', title: 'Through the Painted Woods', year: '', medium: '', w: 936, h: 794 },
  { file: 'art_IMG_7157', title: 'Violet Ridge', year: '', medium: '', w: 940, h: 776 },
  { file: 'art_IMG_7158', title: 'Cherry Blossom Road', year: '', medium: '', w: 978, h: 811 },
  { file: 'art_IMG_7162', title: 'The Little Bridge in October', year: '', medium: '', w: 973, h: 785 },
  { file: 'art_IMG_7165', title: 'Winter Sun, Spinning', year: '', medium: '', w: 1110, h: 1381 },
  { file: 'art_IMG_7167', title: 'The Piano Room', year: '', medium: '', w: 1031, h: 769 },
  { file: 'art_IMG_7208', title: 'Peach Sky Reverie', year: '', medium: '', w: 1110, h: 854 },
  { file: 'art_IMG_8352', title: 'Wine-Dark Sea', year: '', medium: '', w: 680, h: 680, shape: 'oval' },
  { file: 'art_IMG_8478', title: 'Night Swell', year: '', medium: '', w: 637, h: 631, shape: 'oval' },
  { file: 'art_IMG_8538', title: 'Starlight Tide', year: '', medium: '', w: 825, h: 824, shape: 'oval' },
  { file: 'art_IMG_8539', title: 'Clear Day, Round Horizon', year: '', medium: '', w: 738, h: 739, shape: 'oval' },
  { file: 'art_IMG_8664', title: 'Little Gold Sunset', year: '', medium: '', w: 607, h: 403 },
  { file: 'art_IMG_9240', title: 'Blue Rollers', year: '', medium: '', w: 1068, h: 517 },
  { file: 'art_IMG_9342', title: 'Deep Water', year: '', medium: '', w: 873, h: 866 },
  { file: 'art_IMG_9506', title: 'Emerald Falls', year: '', medium: '', w: 1110, h: 537 },
  { file: 'art_IMG_9554a', title: 'Small Worlds: The Cottage', year: '', medium: '', w: 413, h: 422, group: 'small-worlds', groupTitle: 'Small Worlds' },
  { file: 'art_IMG_9554b', title: 'Small Worlds: Flower Rows', year: '', medium: '', w: 366, h: 371, group: 'small-worlds', groupTitle: 'Small Worlds' },
  { file: 'art_IMG_9554c', title: 'Small Worlds: Lavender Shore', year: '', medium: '', w: 285, h: 276, group: 'small-worlds', groupTitle: 'Small Worlds' },
  { file: 'art_IMG_9554d', title: 'Small Worlds: Mountain Sun', year: '', medium: '', w: 285, h: 282, group: 'small-worlds', groupTitle: 'Small Worlds' },
  { file: 'art_IMG_9595', title: 'Open Ocean', year: '', medium: '', w: 707, h: 705 },
  { file: 'art_IMG_9596', title: 'Cobalt Drift', year: '', medium: '', w: 839, h: 829 },
  { file: 'art_IMG_9597', title: 'Blue Ribbon', year: '', medium: '', w: 541, h: 757 },
  { file: 'art_IMG_9603', title: 'Pines on a Starry Lake', year: '', medium: '', w: 629, h: 657 },
  { file: 'art_IMG_9606', title: 'Rose Dunes', year: '', medium: '', w: 912, h: 895 },
  { file: 'art_IMG_9607', title: 'Lilac Evening', year: '', medium: '', w: 854, h: 1059, shape: 'oval' },
  { file: 'art_IMG_9608', title: 'Sea Glass', year: '', medium: '', w: 877, h: 865, shape: 'oval' },
  { file: 'art_IMG_9609', title: 'Green Sea, Pink Moon', year: '', medium: '', w: 856, h: 856 },
  { file: 'art_IMG_9610', title: 'Coral Ripples', year: '', medium: '', w: 624, h: 546 },
  { file: 'art_IMG_9613', title: 'Blue Hour', year: '', medium: '', w: 580, h: 784 },
  { file: 'art_IMG_9615', title: 'Sun-Melted Sea', year: '', medium: '', w: 899, h: 894, shape: 'oval' },
  { file: 'art_IMG_9618', title: 'Graphite Tide', year: '', medium: '', w: 646, h: 646 },
  { file: 'art_IMG_9620', title: 'Indigo Lines', year: '', medium: '', w: 619, h: 613 },
  { file: 'art_IMG_9621', title: 'Desert Hush', year: '', medium: '', w: 670, h: 666 },
  { file: 'art_IMG_9622', title: 'Home by the Pink River', year: '', medium: '', w: 740, h: 986 },
  { file: 'art_IMG_9623', title: 'Teal Morning', year: '', medium: '', w: 707, h: 691 },
];

// ── the brochure you're handed at the door (brochure.js): in the artist's own words ──
export const ABOUT = {
  brand: 'JanGogh Art',
  sections: [
    { title: 'My Background', art: 'art_IMG_5263',
      text: 'I started painting during quarantine of 2020 and the rest is history! Learning by doing the past couple of years, and letting my emotions splash onto the canvas led me here:  JanGogh Art - and I am so glad to have you join me!' },
    { title: 'My Medium', art: 'art_IMG_5261',
      text: 'I love the vibrancy of acrylic paint and the texture of wood panels, gesso panels, and canvases of all sizes.' },
    { title: 'My Inspiration', art: 'art_IMG_5264',
      text: 'My inspiration is taking personality and references from my every day life, expressing it onto the canvas, and then allowing others to connect through that; finding their own personality and experiences within my art.' },
  ],
};
// the collections: "Take me there!" in the brochure tours just these (file names, in order)
export const COLLECTIONS = [
  { name: 'Serene Collection', blurb: 'Seeing the world in flows - the waters, mountains and dunes in this collection are meant to bring you peace and remind you of the fluidity of nature.',
    files: ['art_IMG_9595', 'art_IMG_9240', 'art_IMG_9342', 'art_IMG_9596', 'art_IMG_9597', 'art_IMG_9603', 'art_IMG_9606', 'art_IMG_9609', 'art_IMG_9610', 'art_IMG_9613', 'art_IMG_9618', 'art_IMG_9620', 'art_IMG_9623', 'art_IMG_9621'] },
  { name: 'Zina In Space collection', blurb: 'My small, fluffy dog and her adventures in space!',
    files: ['art_banana_treats_astronaut', 'art_space_heist_mice'] },
  { name: 'Tranquility Collection', blurb: 'My exploration of circle canvases and the movement of our oceans.',
    files: ['art_IMG_8352', 'art_IMG_8478', 'art_IMG_8538', 'art_IMG_8539', 'art_IMG_5557', 'art_IMG_9607', 'art_IMG_9608', 'art_IMG_9615'] },
  { name: 'Serendipity Collection', blurb: "Imagine you're on a hike, out boating and just exploring nature and you find Earth's hidden gems - what does that look like?",
    files: ['art_IMG_0658', 'art_IMG_9506', 'art_IMG_5262', 'art_IMG_5263', 'art_IMG_7162', 'art_IMG_7152', 'art_IMG_2256', 'art_IMG_5265'] },
  { name: 'Enlivened Collection', blurb: 'Looking at the world with the vibrancy of childlike wonder.',
    files: ['art_IMG_5261', 'art_IMG_5264', 'art_IMG_7158', 'art_IMG_7165', 'art_IMG_0471', 'art_IMG_7167', 'art_cows_in_storm', 'art_IMG_9554a', 'art_IMG_9554b', 'art_IMG_9554c', 'art_IMG_9554d'] },
  { name: 'Right before the sun sets Collection', blurb: 'Have you ever caught the sky just as the sun sets? Let me...',
    files: ['art_IMG_7135', 'art_IMG_5271', 'art_IMG_7121', 'art_IMG_7157', 'art_IMG_7208', 'art_IMG_8664', 'art_IMG_9622', 'art_sunset_swell'] },
];
