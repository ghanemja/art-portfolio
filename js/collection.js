// ─── THE COLLECTION ─────────────────────────────────────────────────────────
// Everything the museum shows, in hanging order. Edit freely:
//   file    the image's name in artworks/ (full size: artworks/<file>.jpg; in-world: artworks/web/<file>.webp)
//   title, year, medium, note: shown on the wall card and in the viewer ('' hides a line)
//   w, h    the image's pixel size (only its shape matters: the frame is cut to fit)
// To add a painting: drop <file>.jpg into artworks/, run `python3 scripts/make-web.py`
// (writes the small .webp and prints its row), and add the row here. The hall grows to fit.
export const ARTIST = {
  name: 'Janelle Ghanem',
  museum: 'THE GHANEM GALLERY OF ART',   // carved over the portico
  short: 'THE GHANEM GALLERY',           // on the banners
  tagline: 'paintings, hung in a museum that floats',
  links: [['GitHub', 'https://github.com/ghanemja']],
};

export const WORKS = [
  { file: 'art_banana_treats_astronaut', title: 'Banana Treats for the Astronaut', year: '', medium: '', w: 701, h: 702 },
  { file: 'art_cows_in_storm', title: 'Cows in Storm', year: '', medium: '', w: 1110, h: 807 },
  { file: 'art_space_heist_mice', title: 'Space Heist Mice', year: '', medium: '', w: 698, h: 337 },
  { file: 'art_sunset_swell', title: 'Sunset Swell', year: '', medium: '', w: 717, h: 573 },
  { file: 'art_IMG_0471', title: 'Untitled (No. 0471)', year: '', medium: '', w: 1110, h: 899 },
  { file: 'art_IMG_0658', title: 'Untitled (No. 0658)', year: '', medium: '', w: 1110, h: 880 },
  { file: 'art_IMG_2256', title: 'Untitled (No. 2256)', year: '', medium: '', w: 1110, h: 1084 },
  { file: 'art_IMG_5261', title: 'Untitled (No. 5261)', year: '', medium: '', w: 1110, h: 868 },
  { file: 'art_IMG_5262', title: 'Untitled (No. 5262)', year: '', medium: '', w: 1110, h: 1425 },
  { file: 'art_IMG_5263', title: 'Untitled (No. 5263)', year: '', medium: '', w: 1110, h: 806 },
  { file: 'art_IMG_5264', title: 'Untitled (No. 5264)', year: '', medium: '', w: 1110, h: 866 },
  { file: 'art_IMG_5265', title: 'Untitled (No. 5265)', year: '', medium: '', w: 1110, h: 861 },
  { file: 'art_IMG_5271', title: 'Untitled (No. 5271)', year: '', medium: '', w: 1110, h: 889 },
  { file: 'art_IMG_5557', title: 'Untitled (No. 5557)', year: '', medium: '', w: 1110, h: 1480 },
  { file: 'art_IMG_7121', title: 'Untitled (No. 7121)', year: '', medium: '', w: 1110, h: 872 },
  { file: 'art_IMG_7135', title: 'Untitled (No. 7135)', year: '', medium: '', w: 1110, h: 871 },
  { file: 'art_IMG_7152', title: 'Untitled (No. 7152)', year: '', medium: '', w: 1110, h: 955 },
  { file: 'art_IMG_7157', title: 'Untitled (No. 7157)', year: '', medium: '', w: 1110, h: 924 },
  { file: 'art_IMG_7158', title: 'Untitled (No. 7158)', year: '', medium: '', w: 1110, h: 917 },
  { file: 'art_IMG_7162', title: 'Untitled (No. 7162)', year: '', medium: '', w: 1110, h: 921 },
  { file: 'art_IMG_7165', title: 'Untitled (No. 7165)', year: '', medium: '', w: 1110, h: 1381 },
  { file: 'art_IMG_7167', title: 'Untitled (No. 7167)', year: '', medium: '', w: 1110, h: 916 },
  { file: 'art_IMG_7208', title: 'Untitled (No. 7208)', year: '', medium: '', w: 1110, h: 854 },
  { file: 'art_IMG_8352', title: 'Untitled (No. 8352)', year: '', medium: '', w: 680, h: 680 },
  { file: 'art_IMG_8478', title: 'Untitled (No. 8478)', year: '', medium: '', w: 1110, h: 1480 },
  { file: 'art_IMG_8538', title: 'Untitled (No. 8538)', year: '', medium: '', w: 1110, h: 1468 },
  { file: 'art_IMG_8539', title: 'Untitled (No. 8539)', year: '', medium: '', w: 1110, h: 1381 },
  { file: 'art_IMG_8664', title: 'Untitled (No. 8664)', year: '', medium: '', w: 1110, h: 1480 },
  { file: 'art_IMG_9240', title: 'Untitled (No. 9240)', year: '', medium: '', w: 1110, h: 614 },
  { file: 'art_IMG_9342', title: 'Untitled (No. 9342)', year: '', medium: '', w: 1110, h: 1516 },
  { file: 'art_IMG_9506', title: 'Untitled (No. 9506)', year: '', medium: '', w: 1110, h: 537 },
  { file: 'art_IMG_9554', title: 'Untitled (No. 9554)', year: '', medium: '', w: 1480, h: 1110 },
  { file: 'art_IMG_9595', title: 'Untitled (No. 9595)', year: '', medium: '', w: 707, h: 705 },
  { file: 'art_IMG_9596', title: 'Untitled (No. 9596)', year: '', medium: '', w: 1480, h: 1110 },
  { file: 'art_IMG_9597', title: 'Untitled (No. 9597)', year: '', medium: '', w: 1480, h: 1110 },
  { file: 'art_IMG_9603', title: 'Untitled (No. 9603)', year: '', medium: '', w: 1480, h: 1110 },
  { file: 'art_IMG_9606', title: 'Untitled (No. 9606)', year: '', medium: '', w: 1480, h: 1110 },
  { file: 'art_IMG_9607', title: 'Untitled (No. 9607)', year: '', medium: '', w: 1480, h: 1110 },
  { file: 'art_IMG_9608', title: 'Untitled (No. 9608)', year: '', medium: '', w: 1480, h: 1110 },
  { file: 'art_IMG_9609', title: 'Untitled (No. 9609)', year: '', medium: '', w: 1480, h: 1110 },
  { file: 'art_IMG_9610', title: 'Untitled (No. 9610)', year: '', medium: '', w: 1480, h: 1110 },
  { file: 'art_IMG_9613', title: 'Untitled (No. 9613)', year: '', medium: '', w: 1480, h: 1110 },
  { file: 'art_IMG_9615', title: 'Untitled (No. 9615)', year: '', medium: '', w: 1480, h: 1110 },
  { file: 'art_IMG_9618', title: 'Untitled (No. 9618)', year: '', medium: '', w: 1480, h: 1110 },
  { file: 'art_IMG_9620', title: 'Untitled (No. 9620)', year: '', medium: '', w: 1480, h: 1110 },
  { file: 'art_IMG_9621', title: 'Untitled (No. 9621)', year: '', medium: '', w: 670, h: 666 },
  { file: 'art_IMG_9622', title: 'Untitled (No. 9622)', year: '', medium: '', w: 740, h: 986 },
  { file: 'art_IMG_9623', title: 'Untitled (No. 9623)', year: '', medium: '', w: 1480, h: 1110 },
];
