// ─── THE MUSEUM — lifted from art-heist (js/museum.js), the crime scene made optional ───
// In the portfolio it's built with heist: false: the dome is whole, no police tape, beacons,
// rope or ladder, and the forecourt easel holds a real painting instead of an empty frame.
// frameKit's ornateFrame takes { art } to hang a painting in the frame instead of the cut-out
// canvas the thief left.
// A proper civic museum, modelled (not stacked): a fluted Greek-revival
// portico on a three-tier stylobate, a gabled temple body flanked by two
// lower gallery wings, and a ribbed glass rotunda dome with ONE pane missing —
// that's how the thief got in. Out front: the paved forecourt, police tape,
// blinking beacons, searchlights after dark, an empty gilded frame on an easel.
//
// Everything is smooth-shaded with real bevels (RoundedBox, lathed profiles,
// bevelled extrusions) so it reads curved in Classic, and clean silhouettes so
// the boil hull + inked edge pass draw it well in Sketchbook / Wasteland.
// Static parts are merged per material at the end to keep draw calls low.
//
// Local frame: +Y up, +Z faces the road. The origin is the forecourt where the
// player arrives; the building stands behind it (−Z).
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { mergeGeometries, mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';

const ART = './artworks/';

export function buildMuseum({ lite = false, glowMats = [], artBase = ART, openDoor = false, spin = 0, heist = true,
  name = 'THE DOWNTOWN MUSEUM OF ART', shortName = 'THE DOWNTOWN MUSEUM',
  banners: bannerList = [['art_cows_in_storm.jpg', 'COWS IN STORM'], ['art_IMG_5262.jpg', 'OPENING NIGHT']],
  bannerSub = '45 acrylics · one night only', bannerFoot = 'TONIGHT', easelArt = null } = {}) {
  const g = new THREE.Group();
  g.name = 'DowntownMuseum';
  const SEG = lite ? 24 : 48;
  let ladder = null;

  // ── materials: smooth, a little satin; nothing flat-shaded ──
  const S = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.72, metalness: 0, flatShading: false, ...o });
  const STONE = S(0xf2e8d5);                    // limestone
  const STONE_D = S(0xd8cab0, { roughness: 0.8 });   // steps, shadowed bands
  const TRIM = S(0xfffaf0, { roughness: 0.6 });      // cornices, frames
  const ROOF = S(0x7d8f99, { roughness: 0.55, metalness: 0.25 });   // lead/zinc
  const PATINA = S(0x5fae9a, { roughness: 0.45, metalness: 0.35 });  // copper ribs
  const BRONZE = S(0x7a4f28, { roughness: 0.38, metalness: 0.65 });
  const GOLD = S(0xe3b44c, { roughness: 0.28, metalness: 0.85 });
  const HEDGE = S(0x4f8f4c, { roughness: 0.9 });
  const POT = S(0xb9764a, { roughness: 0.75 });
  const DARK = S(0x2d2138, { roughness: 0.6 });
  const GLASS = new THREE.MeshStandardMaterial({
    color: 0xa9d8ec, roughness: 0.08, metalness: 0.3, transparent: true, opacity: 0.42,
    emissive: 0xffd9a0, emissiveIntensity: 0, side: THREE.DoubleSide, depthWrite: false,
  });
  // gallery windows: warm and lit from inside after dark
  const WIN = new THREE.MeshStandardMaterial({ color: 0x3d5566, roughness: 0.15, metalness: 0.4, emissive: 0xffcf86, emissiveIntensity: 0 });
  const LAMP = new THREE.MeshStandardMaterial({ color: 0xfff3d6, emissive: 0xffdc9a, emissiveIntensity: 0.4, roughness: 0.3 });
  glowMats.push(WIN, LAMP);

  const add = (geo, mat, x = 0, y = 0, z = 0, parent = g) => {
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x, y, z);
    parent.add(m);
    return m;
  };
  // bevel resolution follows size: a big slab's edge is seen up close and
  // needs a round profile; a door panel's 2cm edge only needs one chamfer step
  const rbox = (w, h, d, r = 0.06, seg) => {
    const s2 = seg ?? (Math.max(w, h, d) > 2.5 ? 2 : 1);
    return new RoundedBoxGeometry(w, h, d, lite ? 1 : s2, Math.min(r, w / 2 - 1e-3, h / 2 - 1e-3, d / 2 - 1e-3));
  };
  // smooth a non-indexed / seamed geometry: weld, then recompute normals
  const smooth = (geo, keepUV = false) => {
    if (!keepUV) geo.deleteAttribute('uv');
    geo.deleteAttribute('normal');
    const w = mergeVertices(geo, 1e-4);
    w.computeVertexNormals();
    return w;
  };
  const lathe = (pts, seg = SEG) => smooth(new THREE.LatheGeometry(pts.map(([x, y]) => new THREE.Vector2(x, y)), seg));
  const extrude = (shape, depth, bevel = 0.05, keepUV = false) => smooth(new THREE.ExtrudeGeometry(shape, {
    depth, bevelEnabled: bevel > 0, bevelThickness: bevel, bevelSize: bevel, bevelSegments: lite ? 1 : 3, curveSegments: lite ? 12 : 24,
  }), keepUV);

  // the empty frames (frameKit, below): real museum frames with swept moulding profiles
  const { ornateFrame } = frameKit({ S, GOLD, lite });

  // ── dimensions ──
  const Y0 = 0.66;              // top of the stylobate
  const PZ = 0.45;              // top of the forecourt paving
  const LADDER_Z = -7.5;        // the east-wing ladder (and the rope beside it): between the topiary pots at z -6 and -9
  const COL_Z = -3.6;           // portico column line
  const FRONT = -3.9;           // temple-body / wing front wall
  const BACK = -11.3;
  const ZC = (FRONT + BACK) / 2, DEPTH = FRONT - BACK;
  const CW = 7.8;               // temple body width
  const COL_H = 3.3, COL_R = 0.27;
  const ENT_Y = Y0 + 0.16 + COL_H + 0.12;   // top of the capitals = underside of the entablature
  const ROOF_Y = ENT_Y + 0.36 + 0.5 + 0.2;  // top of the cornice
  const PED_W = 8.9, PED_H = 1.5;

  // ── foundation + three-tier stylobate (the steps wrap the whole building) ──
  add(rbox(13.6, 3.0, 9.2, 0.04, 1), STONE_D, 0, -1.4, -7.0);
  for (let i = 0; i < 3; i++) {
    add(rbox(13.6 - 0.6 * i, 0.22, 9.2 - 0.6 * i, 0.07), i === 2 ? STONE : STONE_D, 0, 0.11 + 0.22 * i, -7.0);
  }

  // ── the portico: six fluted columns with Ionic-ish bases and capitals ──
  const colGeo = (() => {
    const r = COL_R, h = COL_H, P = [];
    P.push([0.001, 0], [r * 1.34, 0], [r * 1.38, 0.05], [r * 1.32, 0.1], [r * 1.18, 0.13], [r * 1.12, 0.17],
      [r * 1.18, 0.21], [r * 1.12, 0.26], [r * 1.0, 0.31]);
    const s0 = 0.31, s1 = h - 0.36, N = 6;
    for (let i = 0; i <= N; i++) {
      const t = i / N;
      P.push([r * (1 - 0.13 * t * t + 0.035 * Math.sin(Math.PI * t)), s0 + (s1 - s0) * t]);   // entasis
    }
    const rt = r * 0.87;
    P.push([rt * 1.1, h - 0.32], [rt * 1.12, h - 0.28], [rt * 1.02, h - 0.25],   // astragal
      [rt * 1.08, h - 0.2], [r * 1.18, h - 0.13], [r * 1.36, h - 0.07], [r * 1.4, h - 0.03], [0.001, h - 0.03]);
    const geo = new THREE.LatheGeometry(P.map(([x, y]) => new THREE.Vector2(x, y)), lite ? 20 : 32);
    if (!lite) {                                   // 8 shallow flutes, sampled 4× each
      const p = geo.attributes.position;
      for (let i = 0; i < p.count; i++) {
        const y = p.getY(i);
        if (y < s0 + 0.04 || y > s1 - 0.02) continue;
        const a = Math.atan2(p.getX(i), p.getZ(i));
        const k = 1 - 0.05 * Math.pow(0.5 + 0.5 * Math.cos(a * 8), 2);
        p.setX(i, p.getX(i) * k); p.setZ(i, p.getZ(i) * k);
      }
    }
    return smooth(geo);
  })();
  const plinthGeo = rbox(0.8, 0.16, 0.8, 0.04);
  const abacusGeo = rbox(0.84, 0.12, 0.84, 0.04);
  const voluteGeo = (() => {
    const v = new THREE.CylinderGeometry(0.1, 0.1, 0.74, 14, 1);
    v.rotateX(Math.PI / 2);
    return v;
  })();
  for (let i = 0; i < 6; i++) {
    const x = -3.25 + i * 1.3;
    if (openDoor && (i === 2 || i === 3)) continue;   // the main app keeps the doorway clear
    add(plinthGeo, STONE, x, Y0 + 0.08, COL_Z);
    add(colGeo, STONE, x, Y0 + 0.16, COL_Z);
    add(abacusGeo, TRIM, x, ENT_Y - 0.06, COL_Z);
    // Ionic volutes: a scroll bolster either side, its spiral end facing out
    for (const sx of [-1, 1]) add(voluteGeo, TRIM, x + sx * 0.3, ENT_Y - 0.2, COL_Z);
  }

  // ── entablature: architrave, frieze (with the carved inscription), cornice ──
  const entD = BACK - 0.1 - (COL_Z + 0.45);
  const entZ = (BACK - 0.1 + COL_Z + 0.45) / 2;
  add(rbox(8.4, 0.36, -entD, 0.05), STONE, 0, ENT_Y + 0.18, entZ);
  add(rbox(8.3, 0.5, -entD - 0.08, 0.04), STONE_D, 0, ENT_Y + 0.36 + 0.25, entZ);
  add(rbox(8.9, 0.2, -entD + 0.4, 0.07), TRIM, 0, ROOF_Y - 0.1, entZ);
  const frontEnt = entZ - entD / 2;   // front face of the architrave (z)
  {
    const cv = document.createElement('canvas'); cv.width = 2048; cv.height = 124;
    const c = cv.getContext('2d');
    c.fillStyle = '#d8cab0'; c.fillRect(0, 0, 2048, 124);
    c.textAlign = 'center'; c.textBaseline = 'middle';
    const txt = name;
    // shrink to fit: with the wide tracking it used to run off both ends ("HE … AR")
    let fs = 78, ls = 26;
    for (; fs > 30; fs -= 2, ls = fs / 3) {
      c.font = `600 ${fs}px Georgia, "Times New Roman", serif`;
      try { c.letterSpacing = `${ls}px`; } catch { /* older canvas */ }
      if (c.measureText(txt).width + ls <= 1880) break;
    }
    // the tracking trails the last letter too: nudge right by half of it to centre
    const cx = 1024 + ls / 2;
    c.fillStyle = '#fff7e6'; c.fillText(txt, cx + 2, 66);       // carved: light lip below…
    c.fillStyle = '#6b5226'; c.fillText(txt, cx, 62);           // …dark cut above
    const tex = new THREE.CanvasTexture(cv);
    tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
    add(new THREE.PlaneGeometry(8.0, 0.48), new THREE.MeshStandardMaterial({ map: tex, roughness: 0.8 }),
      0, ENT_Y + 0.36 + 0.25, frontEnt - 0.03);
  }

  // ── gabled roof + pediment (tympanum, raking cornice, gold medallion) ──
  const tri = (w, h) => { const s = new THREE.Shape(); s.moveTo(-w / 2, 0); s.lineTo(w / 2, 0); s.lineTo(0, h); s.closePath(); return s; };
  const roofLen = -entD + 0.4;
  const roof = add(new THREE.ExtrudeGeometry(tri(PED_W, PED_H), { depth: roofLen, bevelEnabled: false }), [STONE_D, ROOF],
    0, ROOF_Y, entZ - roofLen / 2);
  roof.geometry.computeVertexNormals();
  {
    const frame = tri(PED_W + 0.3, PED_H + 0.22);
    const hole = new THREE.Path(), hw = PED_W - 1.3, hh = PED_H - 0.42;
    hole.moveTo(-hw / 2, 0.2); hole.lineTo(0, 0.2 + hh); hole.lineTo(hw / 2, 0.2); hole.closePath();
    frame.holes.push(hole);
    const fz = entZ + roofLen / 2;
    add(extrude(frame, 0.14, 0.05), TRIM, 0, ROOF_Y - 0.04, fz - 0.06);
    const backFrame = add(extrude(frame, 0.14, 0.05), TRIM, 0, ROOF_Y - 0.04, entZ - roofLen / 2 - 0.1);
    backFrame.rotation.y = Math.PI;
    // the medallion: a gilded painter's palette in a laurel ring
    const cv = document.createElement('canvas'); cv.width = cv.height = 256;
    const c = cv.getContext('2d');
    const gr = c.createRadialGradient(110, 100, 10, 128, 128, 128);
    gr.addColorStop(0, '#fff1b8'); gr.addColorStop(0.55, '#e3b44c'); gr.addColorStop(1, '#9a6b1f');
    c.fillStyle = gr; c.beginPath(); c.arc(128, 128, 126, 0, Math.PI * 2); c.fill();
    c.fillStyle = '#7a5418';
    c.beginPath(); c.ellipse(128, 132, 74, 58, -0.3, 0, Math.PI * 2); c.fill();
    c.fillStyle = '#f6d777';
    c.beginPath(); c.ellipse(124, 126, 70, 54, -0.3, 0, Math.PI * 2); c.fill();
    c.fillStyle = '#7a5418'; c.beginPath(); c.arc(160, 150, 13, 0, Math.PI * 2); c.fill();
    [['#c0392b', 88, 104], ['#2e86de', 116, 90], ['#27ae60', 148, 100], ['#f1c40f', 90, 140]].forEach(([col, x, y]) => {
      c.fillStyle = col; c.beginPath(); c.arc(x, y, 11, 0, Math.PI * 2); c.fill();
    });
    const mt = new THREE.CanvasTexture(cv); mt.colorSpace = THREE.SRGBColorSpace;
    add(new THREE.CircleGeometry(0.42, 40), new THREE.MeshStandardMaterial({ map: mt, roughness: 0.35, metalness: 0.6 }),
      0, ROOF_Y + 0.62, fz + 0.03);
    add(new THREE.TorusGeometry(0.45, 0.045, 10, 48), GOLD, 0, ROOF_Y + 0.62, fz + 0.03);
  }

  // ── temple body: the great hall behind the columns ──
  // (the main app leaves one of the great doors open: there the front wall is a slab with
  // a real doorway through it, WD deep, onto a dim, lamp-lit hall — see the doors below)
  const WD = 0.7, ZB = FRONT - WD, DW = 1.3, DH = 2.0;
  if (!openDoor) {
    add(rbox(CW, ENT_Y - Y0, DEPTH, 0.08), STONE, 0, Y0 + (ENT_Y - Y0) / 2, ZC);
    // rusticated base course + pilasters along the sides
    add(rbox(CW + 0.14, 0.42, DEPTH + 0.14, 0.06), STONE_D, 0, Y0 + 0.21, ZC);
  } else {
    const H = ENT_Y - Y0, sw = (CW - DW) / 2, FD = WD + 0.16, fz = FRONT - FD / 2;   // (the front pieces reach 0.16 into the body: no seam)
    add(rbox(CW, H, ZB - BACK, 0.08), STONE, 0, Y0 + H / 2, (ZB + BACK) / 2);
    for (const s of [-1, 1]) add(rbox(sw, H, FD, 0.08), STONE, s * (DW / 2 + sw / 2), Y0 + H / 2, fz);
    add(rbox(DW + 0.2, H - DH, FD, 0.06), STONE, 0, Y0 + DH + (H - DH) / 2, fz);       // over the doorway
    add(rbox(CW + 0.14, 0.42, ZB - BACK + 0.07, 0.06), STONE_D, 0, Y0 + 0.21, (ZB + BACK - 0.07) / 2);
    for (const s of [-1, 1]) add(rbox(sw + 0.07, 0.42, WD + 0.07 + 0.1, 0.06), STONE_D, s * (DW / 2 + (sw + 0.07) / 2), Y0 + 0.21, FRONT + 0.07 - (WD + 0.17) / 2);
  }
  for (const s of [-1, 1]) for (let k = 0; k < 5; k++) {
    add(rbox(0.12, ENT_Y - Y0 - 0.5, 0.42, 0.04), TRIM, s * (CW / 2 + 0.05), Y0 + (ENT_Y - Y0) / 2 + 0.2, BACK + 0.8 + k * 1.45);
  }
  // the great bronze doors under an arched, glowing fanlight
  {
    const dz = FRONT + 0.02;
    if (!openDoor) {
      add(rbox(1.62, 2.66, 0.16, 0.05), TRIM, 0, Y0 + 1.33, dz);                 // surround
      add(rbox(1.3, 2.0, 0.14, 0.03), BRONZE, 0, Y0 + 1.0, dz + 0.05);            // leaves
      add(rbox(0.03, 1.96, 0.16, 0.01), DARK, 0, Y0 + 1.0, dz + 0.06);            // the gap
      for (const s of [-1, 1]) {                                                  // pulls + panels
        add(new THREE.SphereGeometry(0.045, 12, 8), GOLD, s * 0.1, Y0 + 1.0, dz + 0.14);
        for (const yy of [0.55, 1.4]) add(rbox(0.46, 0.62, 0.04, 0.02), BRONZE, s * 0.33, Y0 + yy, dz + 0.13);
      }
    } else {
      // the main app: the west leaf (museum −x) stands open, swung in on its hinge, so the
      // doorway shows the dim hall inside — the way in. The east leaf stays shut.
      for (const s of [-1, 1]) add(rbox(0.16, 2.66, 0.16, 0.05), TRIM, s * 0.73, Y0 + 1.33, dz);   // surround: jambs…
      add(rbox(1.62, 0.66, 0.16, 0.05), TRIM, 0, Y0 + 2.33, dz);                                  // …and head
      const LZ = FRONT - 0.05, LW = 0.63;
      add(rbox(LW, DH, 0.14, 0.03), BRONZE, DW / 2 - LW / 2 - 0.01, Y0 + DH / 2, LZ);             // the shut leaf
      add(new THREE.SphereGeometry(0.045, 12, 8), GOLD, 0.1, Y0 + 1.0, LZ + 0.09);
      for (const yy of [0.55, 1.4]) add(rbox(0.46, 0.62, 0.04, 0.02), BRONZE, 0.33, Y0 + yy, LZ + 0.08);
      const hinge = new THREE.Group(); hinge.position.set(-DW / 2 + 0.03, Y0, LZ); hinge.rotation.y = 1.28; g.add(hinge);   // swung in ~73°
      add(rbox(LW, DH, 0.14, 0.03), BRONZE, LW / 2, DH / 2, 0, hinge);                            // the open leaf
      add(new THREE.SphereGeometry(0.045, 12, 8), GOLD, LW - 0.11, 1.0, 0.09, hinge);
      for (const yy of [0.55, 1.4]) add(rbox(0.46, 0.62, 0.04, 0.02), BRONZE, LW - 0.33, yy, 0.08, hinge);
      add(new THREE.SphereGeometry(0.045, 12, 8), GOLD, LW - 0.11, 1.0, -0.09, hinge);           // (its inner pull)
      // the hall beyond: dim, with a warm lamp glow low down and an empty gilt frame on the far
      // wall — painted on the reveal's back, unlit (keep: it stays dark in the sun)
      const cv = document.createElement('canvas'); cv.width = 128; cv.height = 192;
      const c = cv.getContext('2d');
      let gr = c.createLinearGradient(0, 0, 0, 192); gr.addColorStop(0, '#120c1a'); gr.addColorStop(0.55, '#241626'); gr.addColorStop(1, '#3a2420');
      c.fillStyle = gr; c.fillRect(0, 0, 128, 192);
      gr = c.createRadialGradient(64, 170, 4, 64, 160, 110); gr.addColorStop(0, 'rgba(255,190,110,0.62)'); gr.addColorStop(0.45, 'rgba(220,140,70,0.22)'); gr.addColorStop(1, 'rgba(220,140,70,0)');
      c.fillStyle = gr; c.fillRect(0, 0, 128, 192);
      c.fillStyle = 'rgba(30,18,22,0.85)'; c.fillRect(0, 150, 128, 42);                  // the far floor, in shadow
      gr = c.createRadialGradient(64, 165, 2, 64, 165, 60); gr.addColorStop(0, 'rgba(255,200,130,0.5)'); gr.addColorStop(1, 'rgba(255,200,130,0)');
      c.fillStyle = gr; c.fillRect(0, 140, 128, 52);                                      // the lamp's pool on it
      c.strokeStyle = 'rgba(214,170,80,0.55)'; c.lineWidth = 5; c.strokeRect(38, 62, 52, 40);   // an empty frame
      c.strokeStyle = 'rgba(120,90,50,0.6)'; c.lineWidth = 1.5; c.strokeRect(44, 68, 40, 28);
      const hall = new THREE.CanvasTexture(cv); hall.colorSpace = THREE.SRGBColorSpace;
      const HALL = new THREE.MeshBasicMaterial({ map: hall }); HALL.userData.keep = true;
      const back = add(new THREE.PlaneGeometry(DW, DH), HALL, 0, Y0 + DH / 2, ZB + 0.01);
      back.userData.noInk = true;
      // the reveal behind the doors: lined dark, a dark floor (the light falls off inside)
      const SHADE = new THREE.MeshBasicMaterial({ color: 0x1d1420 }); SHADE.userData.keep = true;
      const FLOOR = new THREE.MeshBasicMaterial({ color: 0x3a2622 }); FLOOR.userData.keep = true;
      const rd = ZB - (LZ - 0.07);                                                              // from the door's back face to the hall
      for (const s of [-1, 1]) { const m = add(new THREE.PlaneGeometry(-rd, DH), SHADE, s * (DW / 2 - 0.004), Y0 + DH / 2, (ZB + LZ - 0.07) / 2); m.rotation.y = -s * Math.PI / 2; m.userData.noInk = true; }
      { const m = add(new THREE.PlaneGeometry(DW, -rd), SHADE, 0, Y0 + DH - 0.004, (ZB + LZ - 0.07) / 2); m.rotation.x = Math.PI / 2; m.userData.noInk = true; }
      { const m = add(new THREE.PlaneGeometry(DW, -rd + 0.08), FLOOR, 0, Y0 + 0.004, (ZB + LZ) / 2); m.rotation.x = -Math.PI / 2; m.userData.noInk = true; }
    }
    const fan = add(new THREE.CircleGeometry(0.62, 32, 0, Math.PI), WIN, 0, Y0 + 2.02, dz + 0.1);
    fan.scale.y = 0.85;
    const arch = add(new THREE.TorusGeometry(0.66, 0.06, 10, 32, Math.PI), TRIM, 0, Y0 + 2.02, dz + 0.1);
    arch.scale.y = 0.85;
    // two flanking niches, lit
    for (const s of [-1, 1]) {
      add(rbox(0.9, 2.0, 0.1, 0.04), TRIM, s * 2.3, Y0 + 1.45, dz);
      add(rbox(0.7, 1.75, 0.08, 0.03), WIN, s * 2.3, Y0 + 1.4, dz + 0.04);
    }
  }

  // the service door, round the back: a plain steel door for deliveries (the thieves'
  // way out — the tyre ruts in the verge behind it are a clue in the main app)
  if (openDoor) {
    const dz = BACK - 0.02, DY = 0.44;                                         // sill on the second step
    const STEEL = S(0x6f7d78, { roughness: 0.5, metalness: 0.35 });
    add(rbox(1.36, 2.28, 0.14, 0.04), TRIM, 0, DY + 1.14, dz);                  // surround
    add(rbox(1.08, 2.06, 0.1, 0.03), STEEL, 0, DY + 1.03, dz - 0.05);          // the door
    add(rbox(1.0, 0.3, 0.03, 0.01), STEEL, 0, DY + 0.22, dz - 0.11);           // kick plate
    add(rbox(0.78, 0.05, 0.05, 0.02), DARK, 0, DY + 1.0, dz - 0.15);           // push bar
    for (const s of [-1, 1]) add(rbox(0.05, 0.12, 0.08, 0.02), DARK, s * 0.36, DY + 1.0, dz - 0.12);
    add(rbox(0.46, 0.16, 0.02, 0.01), TRIM, 0, DY + 1.7, dz - 0.11);           // DELIVERIES plate
    add(rbox(1.6, 0.08, 0.6, 0.03), STONE_D, 0, DY + 2.42, dz - 0.3);          // a little canopy
    for (const s of [-1, 1]) add(rbox(0.05, 0.05, 0.56, 0.02), TRIM, s * 0.72, DY + 2.34, dz - 0.3);
    add(new THREE.SphereGeometry(0.09, 14, 10), LAMP, 0, DY + 2.3, dz - 0.5);  // the light over it
    // a loading ramp down to the verge (the van backed up to it — the ruts end at its foot):
    // a short landing at sill height, then a gentle slope, over the stylobate's back steps
    {
      const RL = 2.7, land = 0.35, rp = new THREE.Shape();
      rp.moveTo(0, -0.06); rp.lineTo(0, DY); rp.lineTo(land, DY); rp.lineTo(RL, 0.03); rp.lineTo(RL, -0.06); rp.closePath();
      const rg = new THREE.ExtrudeGeometry(rp, { depth: 1.5, bevelEnabled: true, bevelThickness: 0.03, bevelSize: 0.03, bevelSegments: 2 });
      rg.rotateY(Math.PI / 2); rg.translate(-0.75, 0, 0);                       // shape x runs out from the wall (-z)
      add(rg, STONE_D, 0, 0, dz - 0.07);
      for (const s of [-1, 1]) {                                                  // kerbs along its sides
        const kp = new THREE.Shape(); kp.moveTo(0, DY); kp.lineTo(land, DY + 0.08); kp.lineTo(RL, 0.1); kp.lineTo(RL, 0.0); kp.lineTo(land, DY - 0.02); kp.lineTo(0, DY - 0.02); kp.closePath();
        const kg = new THREE.ExtrudeGeometry(kp, { depth: 0.08, bevelEnabled: true, bevelThickness: 0.015, bevelSize: 0.015, bevelSegments: 1 });
        kg.rotateY(Math.PI / 2); kg.translate(s * 0.75 - 0.04, 0, 0);
        add(kg, TRIM, 0, 0, dz - 0.07);
      }
    }
  }

  // ── the two gallery wings: lower, flat-roofed, balustraded, arched windows ──
  const WING_W = 2.5, WING_H = 2.9, WING_X = CW / 2 + WING_W / 2 - 0.05;
  for (const s of [-1, 1]) {
    const wx = s * WING_X;
    add(rbox(WING_W, WING_H, DEPTH - 0.4, 0.08), STONE, wx, Y0 + WING_H / 2, ZC - 0.2);
    add(rbox(WING_W + 0.1, 0.38, DEPTH - 0.3, 0.05), STONE_D, wx, Y0 + 0.19, ZC - 0.2);
    add(rbox(WING_W + 0.3, 0.2, DEPTH - 0.1, 0.07), TRIM, wx, Y0 + WING_H + 0.1, ZC - 0.2);
    // balustrade round the wing's three open sides (front, outer side, back), on the parapet
    // ledge: a post (pedestal + cap) at every corner and both ends, and along the long side; the
    // handrail runs post to post, and the balusters stand evenly between, each on the ledge and
    // under the rail. (The rails used to overshoot the corner, stop short of the other run and
    // hang past the ledge's ends; the front run stood 0.25 out past the ledge, its balusters
    // in the air.)
    const balY = Y0 + WING_H + 0.2, RAIL_Y = balY + 0.42, PW = 0.2, PH = 0.5;
    const hx = (WING_W + 0.3) / 2, hz = (DEPTH - 0.1) / 2, lz = ZC - 0.2;   // the ledge slab
    const xo = wx + s * (hx - 0.13), xi = s * (CW / 2 + PW / 2), zf = lz + hz - 0.13, zb = lz - hz + 0.13;
    const balGeo = lathe([[0.001, 0], [0.07, 0], [0.05, 0.08], [0.09, 0.2], [0.05, 0.32], [0.06, 0.38], [0.001, 0.38]], 8);
    const postGeo = rbox(PW, PH - 0.05, PW, 0.03), capGeo = rbox(PW + 0.06, 0.06, PW + 0.06, 0.02);
    const post = (x, z) => { add(postGeo, TRIM, x, balY + (PH - 0.05) / 2, z); add(capGeo, TRIM, x, balY + PH - 0.03, z); };
    const run = (ax, az, bx, bz) => {                       // post a → post b (axis-aligned)
      const L = Math.hypot(bx - ax, bz - az), along = bx !== ax, len = L - PW + 0.04;
      add(along ? rbox(len, 0.08, 0.1, 0.03) : rbox(0.1, 0.08, len, 0.03), TRIM, (ax + bx) / 2, RAIL_Y, (az + bz) / 2);
      const n = Math.max(1, Math.round((L - PW) / 0.5));
      for (let k = 0; k < n; k++) { const t = (PW / 2 + (k + 0.5) * (L - PW) / n) / L; add(balGeo, TRIM, ax + (bx - ax) * t, balY, az + (bz - az) * t); }
    };
    const sideZ = [zf, zf + (zb - zf) / 3, zf + 2 * (zb - zf) / 3, zb];
    for (const [x, z] of [[xi, zf], [xi, zb], ...sideZ.map(z => [xo, z])]) post(x, z);
    run(xi, zf, xo, zf); run(xi, zb, xo, zb);
    for (let k = 0; k < 3; k++) run(xo, sideZ[k], xo, sideZ[k + 1]);
    // arched gallery windows down the outer wall. The surround is cut to the arch (a square
    // plate stuck out past the curve at both top corners): straight jambs, then a half-round
    // head that meets the arch trim's outer edge (radius 0.43 at the springline, y 0.55)
    const sideX = wx + s * (WING_W / 2 + 0.01);
    const SURR_B = 0.025, surround = new THREE.Shape();
    {
      const hw = 0.43 - SURR_B, yb = -0.75 + SURR_B;              // the bevel adds SURR_B all round
      surround.moveTo(-hw, yb); surround.lineTo(hw, yb); surround.lineTo(hw, 0.55);
      surround.absarc(0, 0.55, hw, 0, Math.PI, false); surround.lineTo(-hw, yb);
    }
    const surroundGeo = extrude(surround, 0.08 - 2 * SURR_B, SURR_B); surroundGeo.translate(0, 0, -(0.08 - 2 * SURR_B) / 2);
    const archGeo = new THREE.TorusGeometry(0.38, 0.05, 8, 24, Math.PI), jambGeo = new THREE.CylinderGeometry(0.05, 0.05, 1.2, 8);
    for (let k = 0; k < 3; k++) {
      const z = BACK + 1.6 + k * 2.1;
      const grp = new THREE.Group(); grp.position.set(sideX, Y0 + 1.25, z); grp.rotation.y = s * Math.PI / 2; g.add(grp);
      add(surroundGeo, TRIM, 0, 0, 0, grp);
      add(new THREE.PlaneGeometry(0.66, 1.2), WIN, 0, -0.05, 0.05, grp);
      add(new THREE.CircleGeometry(0.33, 20, 0, Math.PI), WIN, 0, 0.55, 0.05, grp);
      // one frame all the way round: the arch trim carries on down both jambs to a sill,
      // a transom bar across the springline, and the mullion runs sill to transom
      add(archGeo, TRIM, 0, 0.55, 0.05, grp);
      for (const sx of [-1, 1]) add(jambGeo, TRIM, sx * 0.38, -0.05, 0.05, grp);
      add(rbox(0.9, 0.07, 0.12, 0.025), TRIM, 0, -0.67, 0.05, grp);             // sill
      add(rbox(0.7, 0.05, 0.07, 0.015), TRIM, 0, 0.55, 0.08, grp);              // transom
      add(rbox(0.04, 1.2, 0.06, 0.01), TRIM, 0, -0.05, 0.08, grp);            // mullion
    }
  }

  // ── exhibition banners on the wing fronts: the paintings that were stolen ──
  bannerList.forEach(([fn, title], i) => {
    const s = i ? 1 : -1;
    const cv = document.createElement('canvas'); cv.width = 512; cv.height = 1152;
    const c = cv.getContext('2d');
    c.scale(2, 2);                                     // drawn in 256×576 units, at double resolution
    // every line of lettering fits inside the banner's margins (shrinks to fit, never runs off the edge)
    const fitText = (txt, y, weight, size, family = 'Georgia, serif', maxW = 216) => {
      let px = size; c.font = `${weight} ${px}px ${family}`;
      while (c.measureText(txt).width > maxW && px > 8) { px -= 1; c.font = `${weight} ${px}px ${family}`; }
      c.fillText(txt, 128, y);
    };
    const paint = (img) => {
      c.setTransform(2, 0, 0, 2, 0, 0); c.fillStyle = '#7a1f2b'; c.fillRect(0, 0, 256, 576);
      c.fillStyle = '#e3b44c'; c.fillRect(14, 14, 228, 4); c.fillRect(14, 558, 228, 4);
      c.fillStyle = '#fff4e0'; c.textAlign = 'center';
      fitText(shortName, 50, '600', 22);
      // the painting in a painted gilt frame: gradient bands, a pearl bead, corner bosses
      const gilt = (x, y, w2, h2) => {
        const F = 18;
        const gr = c.createLinearGradient(x - F, y - F, x + w2 + F, y + h2 + F);
        gr.addColorStop(0, '#fff0b0'); gr.addColorStop(0.35, '#e3b44c'); gr.addColorStop(0.7, '#a8761f'); gr.addColorStop(1, '#f2d27a');
        c.fillStyle = gr; c.fillRect(x - F, y - F, w2 + 2 * F, h2 + 2 * F);
        c.strokeStyle = '#7a5418'; c.lineWidth = 3; c.strokeRect(x - F + 2, y - F + 2, w2 + 2 * F - 4, h2 + 2 * F - 4); c.strokeRect(x - 3, y - 3, w2 + 6, h2 + 6);
        c.fillStyle = '#fff4c8';
        for (let t = 0; t < 1; t += 0.035) for (const [px, py] of [[x - 9 + t * (w2 + 18), y - 9], [x - 9 + t * (w2 + 18), y + h2 + 9], [x - 9, y - 9 + t * (h2 + 18)], [x + w2 + 9, y - 9 + t * (h2 + 18)]]) { c.beginPath(); c.arc(px, py, 2.2, 0, Math.PI * 2); c.fill(); }
        for (const [px, py] of [[x - 9, y - 9], [x + w2 + 9, y - 9], [x - 9, y + h2 + 9], [x + w2 + 9, y + h2 + 9]]) {
          c.fillStyle = '#e3b44c'; c.beginPath(); c.arc(px, py, 11, 0, Math.PI * 2); c.fill(); c.stroke();
          c.fillStyle = '#fff0b0'; c.beginPath(); c.arc(px - 3, py - 3, 4, 0, Math.PI * 2); c.fill();
        }
      };
      if (img) {
        const ar = img.width / img.height, bw = 188, bh = Math.min(280, bw / ar);
        gilt(128 - bw / 2, 92, bw, bh);
        c.drawImage(img, 128 - bw / 2, 92, bw, bh);
      } else { gilt(34, 92, 188, 280); c.fillStyle = '#5a1620'; c.fillRect(34, 92, 188, 280); }
      c.fillStyle = '#fff4e0'; fitText(title, 440, '700', 30);
      c.fillStyle = '#f2d39a'; fitText(bannerSub, 478, 'italic', 20);
      fitText(bannerFoot, 530, '600', 18);
    };
    paint(null);
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
    const img = new Image();
    img.onload = () => { paint(img); tex.needsUpdate = true; };
    img.src = artBase + fn;
    const bx = s * WING_X, bz = FRONT + 0.08;
    add(new THREE.PlaneGeometry(1.2, 2.7), new THREE.MeshStandardMaterial({ map: tex, roughness: 0.85, side: THREE.DoubleSide }),
      bx, Y0 + 1.5, bz);
    const rod = add(new THREE.CylinderGeometry(0.03, 0.03, 1.42, 10), BRONZE, bx, Y0 + 2.88, bz);
    rod.rotation.z = Math.PI / 2;
    for (const e of [-1, 1]) add(new THREE.SphereGeometry(0.05, 10, 8), GOLD, bx + e * 0.72, Y0 + 2.88, bz);
  });

  const shardKeep = [];
  // ── the rotunda: drum, ribbed glass dome with ONE pane missing, lantern ──
  const DOME_Z = ZC + 0.4, DRUM_Y = ROOF_Y + 0.85, DOME_R = 1.85;
  {
    add(new THREE.CylinderGeometry(2.0, 2.05, 1.3, SEG), STONE, 0, DRUM_Y, DOME_Z);
    add(new THREE.TorusGeometry(2.04, 0.08, 6, 32), TRIM, 0, DRUM_Y + 0.66, DOME_Z).rotation.x = Math.PI / 2;
    add(new THREE.TorusGeometry(2.08, 0.07, 6, 32), TRIM, 0, DRUM_Y - 0.6, DOME_Z).rotation.x = Math.PI / 2;
    for (let k = 0; k < 16; k++) {           // drum windows + pilasters
      const a = k / 16 * Math.PI * 2;
      const w = add(rbox(0.3, 0.6, 0.08, 0.03), WIN, Math.sin(a) * 2.03, DRUM_Y + 0.05, DOME_Z + Math.cos(a) * 2.03);
      w.rotation.y = a;
      const p = add(rbox(0.1, 1.1, 0.1, 0.03), TRIM, Math.sin(a + 0.196) * 2.06, DRUM_Y, DOME_Z + Math.cos(a + 0.196) * 2.06);
      p.rotation.y = a;
    }
    const dy = DRUM_Y + 0.7;
    // glass in three bands; the middle band skips one pane facing the road
    const PH0 = Math.PI * 0.18, PHL = Math.PI / 6;    // the broken pane's longitude span
    const T1 = 0.55, T2 = 1.05;                        // its latitude band (from the pole)
    const ws = lite ? 24 : 40, hs = lite ? 5 : 8;
    add(new THREE.SphereGeometry(DOME_R, ws, hs, 0, Math.PI * 2, 0, T1), GLASS, 0, dy, DOME_Z);
    if (heist) add(new THREE.SphereGeometry(DOME_R, ws, hs, PH0 + PHL, Math.PI * 2 - PHL, T1, T2 - T1), GLASS, 0, dy, DOME_Z);
    else add(new THREE.SphereGeometry(DOME_R, ws, hs, 0, Math.PI * 2, T1, T2 - T1), GLASS, 0, dy, DOME_Z);
    add(new THREE.SphereGeometry(DOME_R, ws, hs, 0, Math.PI * 2, T2, Math.PI / 2 - T2), GLASS, 0, dy, DOME_Z);
    // copper ribs: 12 meridians + two parallels
    const ribs = [];
    for (let k = 0; k < 12; k++) {
      const t = new THREE.TorusGeometry(DOME_R + 0.01, 0.045, 6, lite ? 10 : 18, Math.PI / 2);
      t.rotateY(-Math.PI / 2);              // quarter arc in the YZ plane, equator → pole
      t.rotateY(k / 12 * Math.PI * 2);
      ribs.push(t);
    }
    for (const th of [T1, T2]) {
      const t = new THREE.TorusGeometry(Math.sin(th) * DOME_R + 0.01, 0.04, 6, SEG);
      t.rotateX(Math.PI / 2); t.translate(0, Math.cos(th) * DOME_R, 0);
      ribs.push(t);
    }
    add(mergeGeometries(ribs.map(r => { r.deleteAttribute('uv'); return r; })), PATINA, 0, dy, DOME_Z);
    // lantern + finial
    const top = dy + DOME_R;
    add(new THREE.CylinderGeometry(0.34, 0.38, 0.5, 24), TRIM, 0, top + 0.2, DOME_Z);
    add(new THREE.CylinderGeometry(0.28, 0.28, 0.32, 24), LAMP, 0, top + 0.3, DOME_Z);
    add(lathe([[0.001, 0], [0.42, 0], [0.4, 0.06], [0.22, 0.28], [0.08, 0.5], [0.001, 0.56]], 24), PATINA, 0, top + 0.45, DOME_Z);
    add(new THREE.SphereGeometry(0.11, 16, 12), GOLD, 0, top + 1.08, DOME_Z);
    if (heist) {
    // ── how they got in: the pane is smashed out, not cut — jagged teeth of glass
    // stand round the hole; a grappling hook is caught on the rib above it, and a
    // knotted rope runs down the dome, across the roof and over the east wing's
    // parapet to the top of the ladder; shards are scattered on the roofs below.
    const SHARD = new THREE.MeshStandardMaterial({ color: 0xd4eef8, roughness: 0.08, metalness: 0.2, transparent: true, opacity: 0.85, side: THREE.DoubleSide });
    const onDome = (th, ph, r = DOME_R) => new THREE.Vector3(Math.sin(th) * Math.sin(ph) * r, dy + Math.cos(th) * r, DOME_Z + Math.sin(th) * Math.cos(ph) * r);
    {
      const tri = [], rnd = (k) => (Math.sin(k * 91.7 + 3.1) * 43758.5453) % 1;
      const edge = (n, f) => { for (let k = 0; k < n; k++) f(k / n, (k + 1) / n, Math.abs(rnd(k + n * 7))); };
      const crack = [];                                     // the jagged edge, traced in ink
      const tooth = (a, b, tip) => { tri.push(...a.toArray(), ...b.toArray(), ...tip.toArray()); crack.push([a, tip, b]); };
      const dT = T2 - T1, dP = PHL;
      edge(7, (u0, u1, r) => tooth(onDome(T1, PH0 + u0 * dP), onDome(T1, PH0 + u1 * dP), onDome(T1 + (0.12 + 0.5 * r) * dT, PH0 + (u0 + u1) / 2 * dP)));          // top edge
      edge(7, (u0, u1, r) => tooth(onDome(T2, PH0 + u0 * dP), onDome(T2, PH0 + u1 * dP), onDome(T2 - (0.12 + 0.45 * r) * dT, PH0 + (u0 + u1) / 2 * dP)));          // bottom
      edge(6, (u0, u1, r) => tooth(onDome(T1 + u0 * dT, PH0), onDome(T1 + u1 * dT, PH0), onDome(T1 + (u0 + u1) / 2 * dT, PH0 + (0.1 + 0.45 * r) * dP)));            // left
      edge(6, (u0, u1, r) => tooth(onDome(T1 + u0 * dT, PH0 + dP), onDome(T1 + u1 * dT, PH0 + dP), onDome(T1 + (u0 + u1) / 2 * dT, PH0 + dP - (0.1 + 0.4 * r) * dP)));
      const tg = new THREE.BufferGeometry(); tg.setAttribute('position', new THREE.Float32BufferAttribute(tri, 3)); tg.computeVertexNormals();
      const teeth = add(tg, SHARD); teeth.userData.noInk = true; shardKeep.push(teeth);
      const INKM = S(0x2a2230, { roughness: 1 });
      const lines = crack.map(([a, t, b]) => new THREE.TubeGeometry(new THREE.CatmullRomCurve3([a, t, b], false, 'catmullrom', 0), 6, 0.012, 4));
      // hairline cracks running out into the neighbouring panes
      for (const [th, ph, dth, dph] of [[T1, PH0 - 0.02, -0.12, -0.1], [T2, PH0 + PHL + 0.02, 0.1, 0.09], [T1 + 0.2, PH0 + PHL + 0.02, -0.05, 0.14], [T2, PH0 + 0.1, 0.14, -0.04]]) {
        const P = [0, 0.4, 0.7, 1].map((k, i) => onDome(th + dth * k + (i % 2 ? 0.015 : 0), ph + dph * k, DOME_R + 0.012));
        lines.push(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(P, false, 'catmullrom', 0), 12, 0.009, 4));
      }
      add(mergeGeometries(lines.map(l => { l.deleteAttribute('uv'); return l; })), INKM).userData.noInk = true;
      // shards: big ones on the main roof under the hole, more on the wing roof by the ladder
      const sg = new THREE.TetrahedronGeometry(1);
      const holeA = PH0 + PHL / 2, base = onDome(T2, holeA, DOME_R * 1.25);
      for (let k = 0; k < 9; k++) {
        const r = Math.abs(rnd(k + 40)), s2 = 0.09 + 0.12 * r;
        const sh = add(sg, SHARD, base.x + (r - 0.5) * 1.2 + k * 0.08, ROOF_Y + 1.0 - k * 0.04, base.z + (Math.abs(rnd(k + 60)) - 0.5) * 1.0);
        sh.scale.set(s2, s2 * 0.25, s2 * 0.7); sh.rotation.set(k * 0.7, k * 1.3, k * 0.4); shardKeep.push(sh);
      }
      for (let k = 0; k < 6; k++) {
        const r = Math.abs(rnd(k + 80)), s2 = 0.07 + 0.09 * r;
        const sh = add(sg, SHARD, WING_X + 0.4 + (r - 0.3) * 1.2, Y0 + WING_H + 0.24, -8.6 + (Math.abs(rnd(k + 90)) - 0.5) * 1.4);
        sh.scale.set(s2, s2 * 0.25, s2 * 0.7); sh.rotation.set(k, k * 2.1, 0.3); shardKeep.push(sh);
      }
    }
    // the grappling hook, caught over the rib at the BOTTOM edge of the hole (the
    // rope hangs from there, so it never runs across the open pane)
    const holeA = PH0 + PHL / 2;
    const hookAt = onDome(T2 + 0.02, holeA, DOME_R + 0.08);
    {
      const H = new THREE.Group(); H.position.copy(hookAt);
      H.lookAt(new THREE.Vector3(0, dy, DOME_Z)); H.rotateX(Math.PI / 2);
      g.add(H);
      const IRON = S(0x3a3440, { roughness: 0.5, metalness: 0.5 });
      add(new THREE.CylinderGeometry(0.03, 0.03, 0.42, 8), IRON, 0, 0.12, 0, H);
      for (let k = 0; k < 3; k++) {
        const t = add(new THREE.TorusGeometry(0.11, 0.022, 6, 12, Math.PI * 0.9), IRON, 0, -0.06, 0, H);
        t.rotation.set(0, k * Math.PI * 2 / 3, Math.PI * 0.55);
      }
      add(new THREE.TorusGeometry(0.05, 0.015, 6, 12), IRON, 0, 0.35, 0, H);
    }
    // the rope: over the dome, down the drum, across the roof slope, down to the
    // wing, over its parapet, hanging beside the top of the ladder
    {
      const roofAt = (x) => ROOF_Y + PED_H * Math.max(0, 1 - Math.abs(x) / (PED_W / 2)) + 0.06;
      const pts = [hookAt.clone()];
      for (let k = 1; k <= 4; k++) pts.push(onDome(T2 + 0.02 + (Math.PI / 2 - T2 - 0.02) * k / 4, holeA + 0.08 * k / 4, DOME_R + 0.06));
      const drumX = Math.sin(holeA + 0.08) * 2.12, drumZ = DOME_Z + Math.cos(holeA + 0.08) * 2.12;
      pts.push(new THREE.Vector3(drumX, DRUM_Y + 0.1, drumZ), new THREE.Vector3(drumX + 0.05, roofAt(drumX) + 0.05, drumZ));
      const zEnd = LADDER_Z;
      for (let k = 1; k <= 4; k++) { const x = drumX + (CW / 2 - drumX) * k / 4, z = drumZ + (zEnd - drumZ) * k / 4; pts.push(new THREE.Vector3(x, roofAt(x), z)); }
      // across the wing roof, over the balustrade's handrail (lying on it, just clear of the
      // ladder's +z rail), and down the outside past the ledge, beside the ladder
      const wingTop = Y0 + WING_H + 0.25, rail = WING_X + (WING_W + 0.3) / 2 - 0.13, railTop = Y0 + WING_H + 0.2 + 0.46, ledge = WING_X + (WING_W + 0.3) / 2;
      pts.push(new THREE.Vector3(CW / 2 + 0.25, wingTop + 0.25, zEnd), new THREE.Vector3(CW / 2 + 0.7, wingTop, zEnd),
        new THREE.Vector3(rail - 0.45, wingTop, zEnd + 0.4), new THREE.Vector3(rail - 0.04, railTop + 0.05, zEnd + 0.5),
        new THREE.Vector3(rail + 0.1, railTop - 0.02, zEnd + 0.5), new THREE.Vector3(ledge + 0.1, wingTop - 0.3, zEnd + 0.52),
        new THREE.Vector3(ledge + 0.12, wingTop - 1.2, zEnd + 0.55));   // hangs beside the ladder, clear of the ledge
      const curve = new THREE.CatmullRomCurve3(pts, false, 'centripetal');
      const ROPE = S(0xc9a46a, { roughness: 0.95 });
      add(new THREE.TubeGeometry(curve, 160, 0.05, 7), ROPE);
      const knot = new THREE.SphereGeometry(0.085, 10, 8);
      for (let k = 1; k < 9; k++) add(knot, ROPE, ...curve.getPointAt(k / 9).toArray());
    }
    }
  }

  // ── forecourt: a round paved plaza with a compass-rose mosaic ──
  {
    const cv = document.createElement('canvas'); cv.width = cv.height = 512;
    const c = cv.getContext('2d');
    c.fillStyle = '#e9dcc3'; c.fillRect(0, 0, 512, 512);
    c.strokeStyle = 'rgba(120,96,70,0.28)'; c.lineWidth = 2;
    for (let r = 40; r < 256; r += 34) { c.beginPath(); c.arc(256, 256, r, 0, Math.PI * 2); c.stroke(); }
    for (let k = 0; k < 32; k++) {
      const a = k / 32 * Math.PI * 2;
      c.beginPath(); c.moveTo(256 + Math.cos(a) * 40, 256 + Math.sin(a) * 40); c.lineTo(256 + Math.cos(a) * 256, 256 + Math.sin(a) * 256); c.stroke();
    }
    c.fillStyle = '#b8894a';
    for (let k = 0; k < 8; k++) {
      const a = k / 8 * Math.PI * 2, L = k % 2 ? 90 : 150;
      c.beginPath();
      c.moveTo(256 + Math.cos(a) * L, 256 + Math.sin(a) * L);
      c.lineTo(256 + Math.cos(a + 0.35) * 26, 256 + Math.sin(a + 0.35) * 26);
      c.lineTo(256, 256);
      c.lineTo(256 + Math.cos(a - 0.35) * 26, 256 + Math.sin(a - 0.35) * 26);
      c.closePath(); c.fill();
    }
    c.strokeStyle = '#b8894a'; c.lineWidth = 6; c.beginPath(); c.arc(256, 256, 176, 0, Math.PI * 2); c.stroke();
    c.lineWidth = 3; c.beginPath(); c.arc(256, 256, 248, 0, Math.PI * 2); c.stroke();
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
    const top = new THREE.MeshStandardMaterial({ map: tex, roughness: 0.85 });
    add(new THREE.CylinderGeometry(3.3, 3.4, 0.5, 64), [STONE_D, top, STONE_D], 0, PZ - 0.25, -0.3);
    add(new THREE.CylinderGeometry(3.4, 3.5, 2.6, 32, 1, true), STONE_D, 0, -1.4, -0.3);   // skirt below grade
    add(new THREE.TorusGeometry(3.32, 0.07, 6, 48), TRIM, 0, PZ, -0.3).rotation.x = Math.PI / 2;
  }

  // ── the crime scene: stanchions + police tape across the steps ──
  if (heist) {
    const cv = document.createElement('canvas'); cv.width = 1024; cv.height = 64;
    const c = cv.getContext('2d');
    c.fillStyle = '#ffd400'; c.fillRect(0, 0, 1024, 64);
    c.fillStyle = '#141414'; c.fillRect(0, 0, 1024, 6); c.fillRect(0, 58, 1024, 6);
    c.font = '900 34px Impact, "Arial Black", sans-serif'; c.textBaseline = 'middle';
    c.fillText('POLICE LINE — DO NOT CROSS — ', 8, 33);
    c.fillText('POLICE LINE — DO NOT CROSS — ', 520, 33);
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
    tex.wrapS = THREE.RepeatWrapping;
    const tapeMat = new THREE.MeshStandardMaterial({ map: tex, side: THREE.DoubleSide, roughness: 0.5 });
    const postGeo = lathe([[0.001, 0], [0.18, 0], [0.18, 0.04], [0.06, 0.08], [0.045, 0.2], [0.045, 1.0], [0.07, 1.04], [0.07, 1.1], [0.001, 1.12]], 16);
    const xs = [-4.2, -1.5, 1.5, 4.2], z = -2.0, y0 = PZ;
    // the outer two stand on the lawn beside the forecourt (it ends at r 3.3), not at its paving
    // height — they floated there, and she stood on their feet — the post stretched so the tape
    // stays level; none of them is ground to stand on
    xs.forEach(x => {
      const foot = Math.hypot(x, z + 0.3) < 3.3 ? y0 : 0.08, post = add(postGeo, BRONZE, x, foot, z);
      post.scale.y = (y0 + 1.12 - foot) / 1.12; post.userData.noGround = true;
    });
    for (let i = 0; i < xs.length - 1; i++) {
      const L = xs[i + 1] - xs[i];
      const geo = new THREE.PlaneGeometry(L, 0.11, 12, 1);
      const p = geo.attributes.position, uv = geo.attributes.uv;
      for (let k = 0; k < p.count; k++) {
        const u = p.getX(k) / L + 0.5;
        p.setY(k, p.getY(k) - Math.sin(u * Math.PI) * 0.12);      // sag
        p.setZ(k, Math.sin(u * Math.PI * 3) * 0.02);              // flutter
        uv.setX(k, u * L / 2.4);
      }
      geo.computeVertexNormals();
      add(geo, tapeMat, (xs[i] + xs[i + 1]) / 2, y0 + 1.02, z);
    }
  }

  // ── beacons (blink red/blue) + searchlights (sweep after dark) ──
  const beaconMats = [
    new THREE.MeshStandardMaterial({ color: 0xff3344, emissive: 0xff1122, emissiveIntensity: 1, roughness: 0.3 }),
    new THREE.MeshStandardMaterial({ color: 0x3377ff, emissive: 0x1144ff, emissiveIntensity: 1, roughness: 0.3 }),
  ];
  const beaconGeo = new THREE.CapsuleGeometry(0.11, 0.12, 6, 14);
  if (heist) [[-3.3, 1.4], [3.3, 1.4]].forEach(([x, z], i) => {
    // they stand on the lawn just off the forecourt (which ends at r 3.3), not at paving height:
    // the foot sits at the lawn and the post stretches up so the light stays where it was
    const foot = 0.08, post = add(lathe([[0.001, 0], [0.2, 0], [0.2, 0.05], [0.05, 0.1], [0.04, 0.9], [0.09, 0.95], [0.001, 0.97]], 16), DARK, x, foot, z);
    post.scale.y = (PZ + 0.97 - foot) / 0.97;
    add(beaconGeo, beaconMats[i], x, PZ + 1.08, z);
  });
  const beamMat = new THREE.MeshBasicMaterial({
    color: 0xfff1c8, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false,
  });
  const beams = [];
  if (heist) for (const s of [-1, 1]) {
    const base = new THREE.Group(); base.position.set(s * 5.3, 0.05, -0.5); g.add(base);
    add(new THREE.CylinderGeometry(0.32, 0.38, 0.16, 24), DARK, 0, 0.08, 0, base);        // turntable
    for (const e of [-1, 1]) add(rbox(0.06, 0.62, 0.14, 0.025), DARK, e * 0.3, 0.45, 0, base);   // yoke
    const head = new THREE.Group(); head.position.y = 0.62; base.add(head);
    add(lathe([[0.001, -0.3], [0.2, -0.3], [0.24, -0.2], [0.26, 0.2], [0.29, 0.26], [0.28, 0.3], [0.001, 0.3]], 24), BRONZE, 0, 0, 0, head);
    add(new THREE.CircleGeometry(0.25, 24), LAMP, 0, 0.305, 0, head).rotation.x = -Math.PI / 2;
    const cone = new THREE.CylinderGeometry(1.6, 0.24, 18, 24, 1, true);
    cone.translate(0, 9.3, 0);
    const beam = add(cone, beamMat, 0, 0, 0, head);
    beam.userData.noCollide = true; beam.userData.noClick = true; beam.userData.gpSkip = true; beam.castShadow = false;
    beam.raycast = () => {};
    beams.push({ head, s });
  }

  // ── the empty frame on the forecourt easel: 45 of these inside, all empty ──
  {
    const ez = 0.6, ex = 2.2;
    const easel = new THREE.Group(); easel.position.set(ex, PZ, ez); easel.rotation.y = -0.45; g.add(easel);
    const WOOD = S(0x8a5a35, { roughness: 0.7 });
    for (const s of [-1, 1]) { const l = add(new THREE.CylinderGeometry(0.04, 0.05, 2.0, 10), WOOD, s * 0.42, 0.95, 0, easel); l.rotation.z = s * 0.14; }
    const back = add(new THREE.CylinderGeometry(0.035, 0.045, 2.0, 10), WOOD, 0, 0.9, -0.38, easel); back.rotation.x = -0.36;
    add(rbox(1.1, 0.06, 0.16, 0.02), WOOD, 0, 0.62, 0.04, easel);
    if (easelArt) {                                   // the portfolio: a real painting, framed to its own shape
      const a = easelArt.image ? easelArt.image.width / easelArt.image.height : 1.3;
      const fw = a >= 1 ? 1.3 : 0.95 * a + 0.3, fh = a >= 1 ? 1.0 / a + 0.3 : 1.25;
      ornateFrame(fw, fh, easel, 'baroque', { art: easelArt }).position.set(0, 0.65 + fh / 2, 0.06);
    } else ornateFrame(1.3, 1.0, easel).position.set(0, 1.15, 0.06);       // (the stretcher, dust board and torn canvas come with it)
    // the little wall-card: stood on the ledge, leaning back on the frame's foot
    add(rbox(0.36, 0.16, 0.02, 0.01), S(0xfff6e6), 0.3, 0.73, 0.1, easel).rotation.x = -0.18;
    // two more of the stolen paintings' frames, carried out and leaned behind it — all empty
    if (heist) for (const [x, z, ry, fw, fh, style] of [[3.05, 0.0, -0.75, 1.0, 0.78, 'walnut'], [2.7, -0.62, -0.45, 0.72, 0.95, 'fluted']]) {
      const lean = new THREE.Group(); lean.position.set(x, PZ, z); lean.rotation.set(0, ry, 0); g.add(lean);
      const f = ornateFrame(fw, fh, lean, style); f.position.set(0, fh / 2 + 0.02, 0); f.rotation.x = -0.2; f.position.z = -Math.sin(0.2) * fh / 2;
    }
  }

  // ── a smooth gilded sculpture on a plinth (the one thing they couldn't lift) ──
  // "Endless Ribbon": a gilded Möbius band standing on edge — one surface, one edge, a half
  // twist so it shows its broad face at the crown and turns edge-on where it balances on a
  // small gilt socket. Its section is a soft dog-bone (beaded edges, a thinner middle) and the
  // beads are burnished (GOLD_HI) so the twist reads even in the flat-painted main app. It
  // stands on a fluted green-marble pedestal with white mouldings, gilt fillets and a bronze
  // plaque, in a warm pool of light. The plinth is static (merged with the museum); the
  // ribbon is its own two-material mesh so it can turn.
  const GOLD_HI = S(0xf8dc8c, { roughness: 0.22, metalness: 0.9 });      // burnished highlights
  const GOLD_LO = S(0xa9741f, { roughness: 0.5, metalness: 0.6 });       // the cove, in shadow
  const lobe = new THREE.SphereGeometry(1, 9, 6);                          // (the plaque's pins)
  const MARBLE = S(0x31544c, { roughness: 0.3, metalness: 0.08 });
  let poolMat = null;
  const sculpture = (() => {
    const px = -2.3, pz = 0.6;
    const at = (geo, mat, y) => add(geo, mat, px, PZ + y, pz);
    const RS = lite ? 32 : 64;
    // ── the pedestal (heights above the paving) ──
    at(lathe([[0.001, 0], [0.44, 0], [0.446, 0.015], [0.446, 0.06], [0.436, 0.08], [0.001, 0.08]], RS), STONE_D, 0);   // the step
    at(lathe([[0.001, 0.08], [0.385, 0.08], [0.396, 0.095], [0.395, 0.12], [0.38, 0.14], [0.35, 0.15],       // torus, scotia, fillet
      [0.335, 0.165], [0.34, 0.18], [0.315, 0.2], [0.001, 0.2]], RS), TRIM, 0);
    const S0 = 0.2, S1 = 0.86, SR = 0.27;
    const shaft = (() => {
      const P = [];
      for (let i = 0; i <= 6; i++) { const t = i / 6; P.push(new THREE.Vector2(SR * (1 - 0.06 * t + 0.02 * Math.sin(Math.PI * t)), S0 + (S1 - S0) * t)); }
      const geo = new THREE.LatheGeometry(P, lite ? 40 : 96);
      if (!lite) {                                  // 12 rounded flutes
        const p = geo.attributes.position;
        for (let i = 0; i < p.count; i++) {
          const y = p.getY(i), a = Math.atan2(p.getX(i), p.getZ(i));
          const e = THREE.MathUtils.smoothstep(y, S0, S0 + 0.06) * (1 - THREE.MathUtils.smoothstep(y, S1 - 0.06, S1));   // flutes die out at both ends
          const k = 1 - 0.045 * e * Math.pow(0.5 + 0.5 * Math.cos(a * 12), 1.5);
          p.setX(i, p.getX(i) * k); p.setZ(i, p.getZ(i) * k);
        }
      }
      return smooth(geo);
    })();
    at(shaft, MARBLE, 0);
    for (const [y, r] of [[S0 + 0.012, SR + 0.004], [S1 - 0.01, SR * 0.96 + 0.006]]) {          // gilt fillets at the shaft's ends
      at(new THREE.TorusGeometry(r, 0.012, 8, RS), GOLD, y).rotation.x = Math.PI / 2;
    }
    at(lathe([[0.001, S1], [0.29, S1], [0.3, S1 + 0.018], [0.285, S1 + 0.035], [0.3, S1 + 0.05],          // astragal, ovolo, abacus
      [0.35, S1 + 0.085], [0.385, S1 + 0.105], [0.395, S1 + 0.12], [0.395, S1 + 0.155], [0.385, S1 + 0.165], [0.001, S1 + 0.165]], RS), TRIM, 0);
    const TOP = S1 + 0.165;                                                                               // 1.025
    // the bronze plaque on the road side, bent round the shaft: three raised gilt lines of lettering + four pins
    const bend = (geo, R) => {
      const p = geo.attributes.position;
      for (let i = 0; i < p.count; i++) { const x = p.getX(i), z = p.getZ(i), a = x / R; p.setX(i, (R + z) * Math.sin(a)); p.setZ(i, (R + z) * Math.cos(a)); }
      geo.computeVertexNormals(); return geo;
    };
    const PY = 0.56, PR = SR * (1 - 0.06 * 0.55) - 0.004;
    at(bend(rbox(0.27, 0.15, 0.022, 0.01, 2), PR + 0.006), BRONZE, PY);
    for (const [w, y] of [[0.17, 0.026], [0.12, -0.004], [0.07, -0.03]]) at(bend(rbox(w, y > 0 ? 0.016 : 0.01, 0.008, 0.004, 1), PR + 0.016), GOLD_HI, PY + y);
    for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
      const a = sx * 0.112 / PR;
      add(lobe, GOLD_LO, px + Math.sin(a) * (PR + 0.018), PZ + PY + sy * 0.052, pz + Math.cos(a) * (PR + 0.018)).scale.setScalar(0.007);
    }
    // the gilt socket the ribbon balances on
    at(lathe([[0.001, 0], [0.13, 0], [0.132, 0.012], [0.08, 0.028], [0.052, 0.05], [0.058, 0.07],
      [0.095, 0.1], [0.122, 0.122], [0.125, 0.135], [0.001, 0.135]], RS), GOLD_LO, TOP);
    const SOCK = TOP + 0.135;

    // ── the ribbon ──
    const A = 0.36, B = 0.43, HT = 0.04;                   // half width / half height of the loop, half thickness
    const curve = (t) => new THREE.Vector3(A * Math.sin(t), -B * Math.cos(t), 0.11 * Math.sin(2 * t));   // a gentle saddle: it leans out of plane
    // N along × M around (M even: the half twist stitches ring N-1 to ring 0 shifted by M/2);
    // kw / kt slim the section (for the boil proxy below)
    const ribbonGeo = (N, M, kw = 1, kt = 1) => {
      const pos = new Float32Array(N * M * 3), idx = [], hi = [];
      const T = new THREE.Vector3(), Nn = new THREE.Vector3(), Bn = new THREE.Vector3(), c = new THREE.Vector3();
      for (let i = 0; i < N; i++) {
        const t = i / N * Math.PI * 2;
        c.copy(curve(t));
        T.copy(curve(t + 1e-3)).sub(curve(t - 1e-3)).normalize();
        Nn.copy(c).addScaledVector(T, -c.dot(T)).normalize();        // outward from the loop's centre, square to the path
        Bn.crossVectors(T, Nn);
        const phi = Math.PI / 2 + t / 2;                               // the half twist: edge-on at the foot, face-on at the crown
        const hw = kw * (0.09 + 0.075 * (0.5 - 0.5 * Math.cos(t)));   // slimmer at the foot, broad at the crown
        const cp = Math.cos(phi), sp = Math.sin(phi);
        for (let j = 0; j < M; j++) {
          const s = j / M * Math.PI * 2, cs = Math.cos(s), ss = Math.sin(s);
          const uu = Math.sign(cs) * Math.pow(Math.abs(cs), 0.3);     // a soft superellipse…
          const u = hw * uu;
          const v = kt * HT * Math.sign(ss) * Math.pow(Math.abs(ss), 0.6) * (0.55 + 0.75 * Math.pow(Math.abs(uu), 8));   // …thicker at its beaded edges
          const k = (i * M + j) * 3;
          pos[k] = c.x + (u * cp + v * sp) * Nn.x + (-u * sp + v * cp) * Bn.x;
          pos[k + 1] = c.y + (u * cp + v * sp) * Nn.y + (-u * sp + v * cp) * Bn.y;
          pos[k + 2] = c.z + (u * cp + v * sp) * Nn.z + (-u * sp + v * cp) * Bn.z;
        }
      }
      for (let i = 0; i < N; i++) {
        const i1 = (i + 1) % N, off = i1 === 0 ? M / 2 : 0;           // after one lap the section has turned half way
        for (let j = 0; j < M; j++) {
          const j1 = (j + 1) % M;
          const a = i * M + j, b = i * M + j1, c2 = i1 * M + (j + off) % M, d = i1 * M + (j1 + off) % M;
          const sm = Math.cos((j + 0.5) / M * Math.PI * 2);           // this facet's place round the section
          (Math.abs(sm) > 0.8 ? hi : idx).push(a, c2, b, b, c2, d);
        }
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      geo.setIndex([...idx, ...hi]);
      geo.computeVertexNormals();
      { // wind it outward whatever the parametrisation turned out to be
        const n = geo.attributes.normal, p0 = new THREE.Vector3().fromBufferAttribute(geo.attributes.position, 0);
        if (new THREE.Vector3().fromBufferAttribute(n, 0).dot(p0.sub(curve(0))) < 0) {
          const I = geo.index.array; for (let q = 0; q < I.length; q += 3) { const tmp = I[q + 1]; I[q + 1] = I[q + 2]; I[q + 2] = tmp; }
          geo.computeVertexNormals();
        }
      }
      geo.addGroup(0, idx.length, 0); geo.addGroup(idx.length, hi.length, 1);
      geo.computeBoundingSphere();
      return geo;
    };
    const ribbon = new THREE.Group();
    ribbon.position.set(px, PZ + SOCK + B - 0.006, pz);
    g.add(ribbon);
    const rm = add(ribbonGeo(lite ? 96 : 168, lite ? 14 : 24), [GOLD, GOLD_HI], 0, 0, 0, ribbon);
    if (!lite) rm.castShadow = true;
    // The classic game's Wasteland boil jitters each vertex of its hull. On a mesh this dense
    // and this thin, the jitter spikes through the faces as hairy scratches. So the boil is
    // drawn round a coarse proxy instead: a slightly slimmer ribbon whose own fill never draws
    // (a hidden ShaderMaterial, which flatOf and the main app's restyle leave alone, so it costs
    // no draw call). The gold ribbon still swaps to its Wasteland fill; only its own boil is
    // opted out. The main app's clip-space ink has no jitter and outlines the real ribbon.
    rm.userData._gpDone = true;
    const proxy = add(ribbonGeo(lite ? 48 : 72, 12, 0.96, 0.85), new THREE.ShaderMaterial({ visible: false }), 0, 0, 0, ribbon);
    proxy.userData._gpForce = true; proxy.userData.noInk = true; proxy.userData.noCollide = true; proxy.userData.noClick = true;
    proxy.castShadow = false; proxy.raycast = () => {};

    // ── a warm pool of light on the paving round its foot ──
    {
      const cv = document.createElement('canvas'); cv.width = cv.height = 128;
      const c2 = cv.getContext('2d'), gr = c2.createRadialGradient(64, 64, 0, 64, 64, 64);
      gr.addColorStop(0, 'rgba(255,214,140,1)'); gr.addColorStop(0.45, 'rgba(255,200,120,0.75)'); gr.addColorStop(1, 'rgba(255,190,110,0)');
      c2.fillStyle = gr; c2.fillRect(0, 0, 128, 128);
      const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
      poolMat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity: 0.3, depthWrite: false, blending: THREE.AdditiveBlending,
        fog: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
      const pool = add(new THREE.CircleGeometry(0.8, 40).rotateX(-Math.PI / 2), poolMat, px, PZ + 0.006, pz);
      pool.userData.noCollide = true; pool.userData.noClick = true; pool.userData.gpSkip = true; pool.userData.noInk = true;
      pool.castShadow = false; pool.renderOrder = 1; pool.raycast = () => {};
    }
    return ribbon;
  })();

  // ── lamps, topiary, planters ──
  const lampGeo = lathe([[0.001, 0], [0.16, 0], [0.16, 0.08], [0.08, 0.14], [0.06, 0.3], [0.045, 0.32], [0.04, 2.0], [0.07, 2.04], [0.07, 2.08], [0.001, 2.1]], 16);
  for (const [x, z] of [[-3.9, -1.0], [3.9, -1.0], [-6.2, -2.0], [6.2, -2.0]]) {
    if (openDoor && x === 6.2) continue;                  // the main app's guard booth stands here (museum +x is the town's -x)
    add(lampGeo, DARK, x, 0.15, z);
    add(new THREE.SphereGeometry(0.2, 14, 10), LAMP, x, 2.42, z);
    add(new THREE.CylinderGeometry(0.1, 0.13, 0.08, 16), DARK, x, 2.24, z);
  }
  const potGeo = lathe([[0.001, 0], [0.3, 0], [0.36, 0.42], [0.4, 0.46], [0.001, 0.46]], 20);
  for (const s of [-1, 1]) {
    for (const z of [-2.8, -6.0, -9.0]) {
      const x = s * 7.15;
      add(potGeo, POT, x, -0.05, z).userData.noGround = true;
      add(new THREE.SphereGeometry(0.42, 14, 10), HEDGE, x, 0.82, z).userData.noGround = true;
    }
    // a clipped hedge along the front of each wing (a prop: never a floor to stand on)
    add(rbox(2.0, 0.5, 0.45, 0.14, 2), HEDGE, s * WING_X, Y0 + 0.25, FRONT + 0.4).userData.noGround = true;
  }

  // ── the ladder: someone propped it to the east wing roof ──
  if (heist) {
    const lad = new THREE.Group();
    // leaning like a real ladder: its rails rest ON the balustrade's handrail — touching its
    // outer top edge — and run on 0.35 past it, the lean (0.3, ~1 in 3.3) steep enough to
    // clear the ledge below, and the feet on the lawn out from the wall. (It stood off the
    // ledge before, touching nothing.)
    const LT = 0.3, RR = 0.035, footY = 0.08;
    const ex = WING_X + (WING_W + 0.3) / 2 - 0.13 + 0.05, ey = Y0 + WING_H + 0.2 + 0.46;   // the handrail's outer top edge
    const ax = ex + RR * Math.cos(LT), ay = ey + RR * Math.sin(LT);          // the rail's axis there, one radius out
    const reach = (ay - footY) / Math.cos(LT), LL = reach + 0.35;
    lad.position.set(ax + reach * Math.sin(LT), footY, LADDER_Z);
    lad.rotation.z = LT;
    g.add(lad);
    ladder = { foot: lad.position.clone(), rest: new THREE.Vector3(ax, ay, LADDER_Z), lean: LT };   // (museum-local: the story's clue sparkles on it)
    const ALU = S(0xb8c0c8, { roughness: 0.35, metalness: 0.7 });
    // (the rails run on 0.12 below the foot: the feet are sunk into the ground, never stood on top of it)
    for (const s of [-1, 1]) add(new THREE.CylinderGeometry(0.035, 0.035, LL + 0.12, 8), ALU, 0, (LL - 0.12) / 2, s * 0.24, lad);
    for (let k = 0; k < Math.floor((LL - 0.35) / 0.33); k++) {
      const r = add(new THREE.CylinderGeometry(0.022, 0.022, 0.48, 6), ALU, 0, 0.25 + k * 0.33, 0, lad);
      r.rotation.x = Math.PI / 2;
    }
  }

  // ── merge static parts per material: one draw per material, not ~400 ──
  const keep = new Set([...shardKeep]);
  sculpture.traverse(o => keep.add(o));
  g.traverse(o => { if (o.material === beamMat || beaconMats.includes(o.material)) keep.add(o); });
  for (const b of beams) b.head.traverse(o => keep.add(o));
  g.updateMatrixWorld(true);
  const inv = new THREE.Matrix4().copy(g.matrixWorld).invert();
  const buckets = new Map();
  g.traverse(o => {
    if (!o.isMesh || keep.has(o) || Array.isArray(o.material) || o.material.map) return;
    if (o.material === GLASS) return;     // keep the transparent shell separate
    const geo = o.geometry.clone();
    geo.applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld));
    for (const k of Object.keys(geo.attributes)) if (k !== 'position' && k !== 'normal') geo.deleteAttribute(k);
    if (!geo.index) {
      const n = geo.attributes.position.count, idx = new (n > 65535 ? Uint32Array : Uint16Array)(n);
      for (let i = 0; i < n; i++) idx[i] = i;
      geo.setIndex(new THREE.BufferAttribute(idx, 1));
    }
    if (!buckets.has(o.material)) buckets.set(o.material, { geos: [], meshes: [] });
    const b = buckets.get(o.material); b.geos.push(geo); b.meshes.push(o);
  });
  for (const [mat, b] of buckets) {
    if (b.meshes.length < 2) continue;
    const merged = mergeGeometries(b.geos, false);
    if (!merged) continue;
    for (const m of b.meshes) m.parent.remove(m);
    const mm = new THREE.Mesh(merged, mat);
    mm.userData._gpForce = true;          // large merged parts still get the boil hull
    g.add(mm);
  }
  // drop now-empty helper groups
  const empties = [];
  g.traverse(o => { if (o !== g && o.isGroup && o.children.length === 0) empties.push(o); });
  for (const e of empties) e.parent.remove(e);

  // ── per-frame life ──
  const tick = (t, dayK) => {
    const night = 1 - dayK;
    GLASS.emissiveIntensity = 0.35 * night;
    // beacons alternate, a quick double-flash each
    const ph = (t * 1.6) % 1;
    const flashA = (ph < 0.12 || (ph > 0.22 && ph < 0.34)) ? 1 : 0.08;
    const flashB = (ph > 0.5 && ph < 0.62) || (ph > 0.72 && ph < 0.84) ? 1 : 0.08;
    beaconMats[0].emissiveIntensity = 0.3 + 2.4 * flashA;
    beaconMats[1].emissiveIntensity = 0.3 + 2.4 * flashB;
    beamMat.opacity = 0.11 * THREE.MathUtils.smoothstep(night, 0.25, 0.8);
    poolMat.opacity = 0.22 + 0.4 * night + 0.04 * Math.sin(t * 1.3);   // the sculpture's light, brighter after dark
    if (spin) sculpture.rotation.y = t * spin;                       // (the classic game turns it itself)
    for (const b of beams) {
      b.head.rotation.z = b.s * (0.32 + Math.sin(t * 0.45 + b.s) * 0.22);
      b.head.rotation.x = Math.sin(t * 0.33 + b.s * 2) * 0.28 - 0.08;
    }
  };

  return {
    group: g,
    sculpture,
    tick,
    npcLocal: new THREE.Vector3(0.9, PZ, -1.2),       // the director waits at the foot of the steps
    gemY: DRUM_Y + 0.7 + DOME_R + 1.9,
    gemZ: DOME_Z,
    footCenterZ: -7.0, footRadius: 7.6,
    ladder,
  };
}

// ─── THE EMPTY FRAMES: a kit, shared with the crime-scene room inside (js/rooms.js) ───
// S(color, opts) makes a material (the classic game's satin MeshStandard here; the room
// passes its toon paint), GOLD the main gilt. Returns ornateFrame(w, h, parent, style, opts).
export function frameKit({ S = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.72, metalness: 0, flatShading: false, ...o }),
  GOLD = S(0xe3b44c, { roughness: 0.28, metalness: 0.85 }), lite = false } = {}) {
  const add = (geo, mat, x = 0, y = 0, z = 0, parent) => {
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x, y, z);
    parent.add(m);
    return m;
  };
  const rbox = (w, h, d, r = 0.06, seg = 1) => new RoundedBoxGeometry(w, h, d, lite ? 1 : seg, Math.min(r, w / 2 - 1e-3, h / 2 - 1e-3, d / 2 - 1e-3));
  const smooth = (geo) => {
    geo.deleteAttribute('uv'); geo.deleteAttribute('normal');
    const w = mergeVertices(geo, 1e-4); w.computeVertexNormals(); return w;
  };
  // ── the empty frames: real museum frames, each with a moulding PROFILE swept round the
  // rectangle (mitred corners: one strip per side, smooth across the profile, creased at the
  // mitre), carved ornament on top, and behind the sight edge the bare stretcher, the dust
  // board and ragged strips of the painted canvas the thief's knife left in the rebate.
  // The gold is a gradient by part: pale burnished highlights on what's raised, the main gilt,
  // a deep ochre in the cove, so it reads in the flat-painted main app (one colour per
  // material) as well as in the lit classic game.
  // style: 'baroque' (Louis XV gilt: rocaille shells, acanthus breaking past the edge, pearls,
  // egg-and-dart) · 'walnut' (dark carved walnut, leaf-and-dart, a gilt slip) ·
  // 'fluted' (Dutch: a wide fluted gilt band, ribbon-and-stick sight edge, corner rosettes)
  // Origin at its centre, face to +Z. w, h: outer size.
  const GOLD_HI = S(0xf8dc8c, { roughness: 0.22, metalness: 0.9 });      // burnished highlights
  const GOLD_LO = S(0xa9741f, { roughness: 0.5, metalness: 0.6 });       // the cove, in shadow
  const WALNUT = S(0x4a2a1a, { roughness: 0.5 }), WALNUT_HI = S(0x7a4a2c, { roughness: 0.45 });
  const RAWWOOD = S(0xc9a46e, { roughness: 0.85 }), DUSTBOARD = S(0x3f2e22, { roughness: 1 });
  // a repeatable little random (so every load tears the same rags)
  const rnd = (() => { let s = 7; return () => ((s = (s * 16807) % 2147483647) / 2147483647); })();
  // the moulding: prof = [[inset, height], ...], a closed loop (front from the outer edge to
  // the sight edge, then down and back under); a repeated point creases there
  const sweep = (w, h, prof, mat, parent) => {
    const pos = [], idx = [];
    for (const [a, c] of [[[-1, -1], [1, -1]], [[1, -1], [1, 1]], [[1, 1], [-1, 1]], [[-1, 1], [-1, -1]]]) {
      const base = pos.length / 3;
      for (const [d, z] of prof) {
        const hx = w / 2 - d, hy = h / 2 - d;
        pos.push(a[0] * hx, a[1] * hy, z, c[0] * hx, c[1] * hy, z);
      }
      for (let i = 0; i < prof.length - 1; i++) { const p = base + i * 2; idx.push(p, p + 1, p + 2, p + 1, p + 3, p + 2); }
    }
    const g2 = new THREE.BufferGeometry();
    g2.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g2.setIndex(idx); g2.computeVertexNormals();
    return add(g2, mat, 0, 0, 0, parent);
  };
  // a smooth run of profile points through control points
  const profile = (ctrl, n = 18) => new THREE.SplineCurve(ctrl.map(([d, z]) => new THREE.Vector2(d, z))).getPoints(n).map(v => [v.x, v.y]);
  // close a front profile into a loop: down the inside, across the back, up the outside
  const closeLoop = (front, back = -0.03) => {
    const f0 = front[0], f1 = front[front.length - 1];
    return [[f0[0], back], f0, f0, ...front.slice(1, -1), f1, f1, [f1[0], back], [f1[0], back], [f0[0], back], [f0[0], back]];
  };
  // points spaced along the four sides at an inset, each with its side's direction
  const alongSides = (w, h, d, step, skip = () => false) => {
    const out = [], hx = w / 2 - d, hy = h / 2 - d;
    for (const [x0, y0, x1, y1] of [[-hx, -hy, hx, -hy], [hx, -hy, hx, hy], [hx, hy, -hx, hy], [-hx, hy, -hx, -hy]]) {
      const n = Math.max(2, Math.round(Math.hypot(x1 - x0, y1 - y0) / step)), ang = Math.atan2(y1 - y0, x1 - x0);
      for (let k = 1; k < n; k++) { const x = x0 + (x1 - x0) * k / n, y = y0 + (y1 - y0) * k / n; if (!skip(x, y)) out.push([x, y, ang, k]); }
    }
    return out;
  };
  // ornament parts
  const lobe = new THREE.SphereGeometry(1, lite ? 7 : 9, lite ? 5 : 6);
  const leafGeo = (() => {                       // an acanthus leaf: lobed edges, bevelled, curled and cupped
    const N = 16, half = (x) => 0.2 * Math.pow(Math.sin(Math.PI * Math.min(1, x * 1.08)), 0.7) * (0.72 + 0.28 * Math.abs(Math.cos(x * Math.PI * 3.5)));
    const s = new THREE.Shape(); s.moveTo(0, 0);
    for (let i = 1; i <= N; i++) { const x = i / N; s.lineTo(x, half(x)); }
    for (let i = N - 1; i >= 1; i--) { const x = i / N; s.lineTo(x, -half(x)); }
    s.closePath();
    const g2 = new THREE.ExtrudeGeometry(s, { depth: 0.04, bevelEnabled: true, bevelThickness: 0.05, bevelSize: 0.035, bevelSegments: 1, curveSegments: 4 });
    const p = g2.attributes.position;
    for (let i = 0; i < p.count; i++) { const x = p.getX(i), y = p.getY(i); p.setZ(i, p.getZ(i) + 0.1 * Math.sin(Math.PI * x) + 0.4 * Math.pow(x, 4) - 0.6 * y * y); }
    return smooth(g2);
  })();
  const scrollGeo = new THREE.TorusGeometry(1, 0.22, 6, 14, Math.PI * 1.6);
  const leaf = (P, x, y, z, ang, len, mat, tilt = 0.25) => { const m = add(leafGeo, mat, x, y, z, P); m.scale.set(len, len, len * 0.6); m.rotation.set(0, -tilt, ang); return m; };
  const cscroll = (P, x, y, z, ang, r, mat, flip = false) => {
    const m = add(scrollGeo, mat, x, y, z, P); m.scale.setScalar(r); m.rotation.set(flip ? Math.PI : 0, 0, ang);
    add(lobe, mat, x + Math.cos(ang) * r, y + Math.sin(ang) * r * (flip ? -1 : 1), z, P).scale.setScalar(r * 0.32);   // the curl's knob
    return m;
  };
  // a rocaille shell: ribs fanning out from a boss
  const shell = (P, x, y, z, ang, R, ribs, matHi, matLo) => {
    for (let k = 0; k < ribs; k++) {
      const t = k / (ribs - 1) - 0.5, a = ang + t * 2.1, L = R * (0.75 + 0.25 * Math.cos(t * Math.PI));
      const r = add(lobe, k % 2 ? matLo : matHi, x + Math.cos(a) * L * 0.5, y + Math.sin(a) * L * 0.5, z + (k % 2 ? -0.004 : 0.004), P);
      r.scale.set(L * 0.52, R * 0.13, R * 0.16); r.rotation.z = a;
    }
    add(lobe, matHi, x, y, z + R * 0.12, P).scale.set(R * 0.3, R * 0.3, R * 0.22);
  };
  // the cut-out canvas: bare stretcher, dust board, ragged painted strips left in the rebate
  const RAG = (() => {
    const cv = document.createElement('canvas'); cv.width = 256; cv.height = 64;
    const c = cv.getContext('2d');
    c.fillStyle = '#c9b996'; c.fillRect(0, 0, 256, 64);                                    // primed canvas, aged
    for (let i = 0; i < 70; i++) {                                                            // the painting's edge: oil dabs
      c.fillStyle = ['#2c4a5e', '#3f5f3c', '#55704a', '#2c4a5e', '#b08a3e', '#3a3348'][i % 6];
      c.beginPath(); c.ellipse(rnd() * 256, 14 + rnd() * 50, 10 + rnd() * 18, 4 + rnd() * 6, rnd() * 0.6 - 0.3, 0, Math.PI * 2); c.fill();
    }
    c.fillStyle = '#b9a884'; c.fillRect(0, 0, 256, 10);                                     // the unpainted tacking margin
    const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = THREE.RepeatWrapping;
    return S(0xffffff, { map: t, roughness: 0.95, side: THREE.DoubleSide });
  })();
  const tornRect = (F, ow, oh, z0) => {
    const T = 0.045, bw = 0.05, hx = ow / 2 + 0.02, hy = oh / 2 + 0.02;                       // stretcher bars, tucked under the sight edge
    for (const [x, y, lw, lh] of [[0, -hy + bw / 2, ow + 0.04, bw], [0, hy - bw / 2, ow + 0.04, bw], [-hx + bw / 2, 0, bw, oh + 0.04], [hx - bw / 2, 0, bw, oh + 0.04]])
      add(rbox(lw, lh, T, 0.008, 1), RAWWOOD, x, y, z0 - T / 2, F);
    add(rbox(bw * 0.9, oh, T * 0.8, 0.008, 1), RAWWOOD, 0, 0, z0 - T * 0.6, F);             // the centre brace
    if (ow > 0.8) add(rbox(ow, bw * 0.9, T * 0.8, 0.008, 1), RAWWOOD, 0, 0, z0 - T * 0.65, F);
    add(new THREE.PlaneGeometry(ow + 0.04, oh + 0.04), DUSTBOARD, 0, 0, z0 - T - 0.004, F);  // the dust board behind
    // the rags: a strip along each inner edge, its inside edge torn, two flaps curling forward
    const ex = ow / 2, ey = oh / 2;
    for (const [x0, y0, x1, y1, nx, ny] of [[-ex, -ey, ex, -ey, 0, 1], [ex, -ey, ex, ey, -1, 0], [ex, ey, -ex, ey, 0, -1], [-ex, ey, -ex, -ey, 1, 0]]) {
      const L = Math.hypot(x1 - x0, y1 - y0), N = Math.max(8, Math.round(L / 0.03));
      const s = new THREE.Shape(); s.moveTo(x0 - nx * 0.02, y0 - ny * 0.02);
      for (let k = 0; k <= N; k++) {
        const t = k / N, dep = 0.014 + rnd() * 0.012 + (rnd() < 0.08 ? 0.02 : 0);
        s.lineTo(x0 + (x1 - x0) * t + nx * dep, y0 + (y1 - y0) * t + ny * dep);
      }
      s.lineTo(x1 - nx * 0.02, y1 - ny * 0.02); s.closePath();
      const sg = new THREE.ShapeGeometry(s), uv = sg.attributes.uv, p = sg.attributes.position;
      for (let i = 0; i < uv.count; i++) {                                                   // the painted edge runs along the strip
        const along = ((p.getX(i) - x0) * (x1 - x0) + (p.getY(i) - y0) * (y1 - y0)) / L;
        const across = (p.getX(i) - x0) * nx + (p.getY(i) - y0) * ny;
        uv.setXY(i, along * 3, 0.15 + across * 12);
      }
      add(sg, RAG, 0, 0, z0 + 0.003, F);
      for (const t of [0.3 + rnd() * 0.4]) {                                                   // a flap peeling forward
        const fl = new THREE.Shape(); fl.moveTo(-0.025, 0); fl.lineTo(0.025, 0); fl.lineTo(0.008, 0.045 + rnd() * 0.02); fl.lineTo(-0.01, 0.035); fl.closePath();
        const m = add(new THREE.ShapeGeometry(fl), RAG, x0 + (x1 - x0) * t + nx * 0.01, y0 + (y1 - y0) * t + ny * 0.01, z0 + 0.004, F);
        m.rotation.set(0, 0, Math.atan2(ny, nx) - Math.PI / 2); m.rotateX(-0.5 - rnd() * 0.4);
      }
    }
  };

  let emptied = tornRect, emptiedPath = null;
  // ── more frames: finishes, shapes, and profiles swept round any outline ──
  // finish: the three tones (main, raised highlight, shadowed cove) of a frame's surface
  const FIN = {};
  const finishMats = (f) => FIN[f] || (FIN[f] = (({
    antique: () => [S(0xb48c3c, { roughness: 0.45, metalness: 0.6 }), S(0xd9bb6e, { roughness: 0.35, metalness: 0.7 }), S(0x6e4f22, { roughness: 0.6, metalness: 0.4 })],
    walnut: () => [WALNUT, GOLD, S(0x2e1a10, { roughness: 0.6 })],          // dark walnut, a gilt lip
    silver: () => [S(0xbfc4ca, { roughness: 0.3, metalness: 0.85 }), S(0xf0f2f4, { roughness: 0.22, metalness: 0.9 }), S(0x7e848e, { roughness: 0.5, metalness: 0.6 })],
  })[f] || (() => [GOLD, GOLD_HI, GOLD_LO]))());
  // styles swept round any outline: 'deep' (a deep-moulded ogee and cove, a bead run),
  // 'scallop' (a scalloped outer rim), 'corners' (a plain moulding, carved corners / crest)
  const PATH_STYLES = new Set(['deep', 'scallop', 'corners']);
  // the frame's OUTER edge, counter-clockwise, as [x, y, isCorner]
  const outline = (w, h, shape) => {
    const P = [];
    if (shape === 'oval') {
      const N = lite ? 48 : 72;
      for (let i = 0; i < N; i++) { const a = i / N * Math.PI * 2 - Math.PI / 2; P.push([w / 2 * Math.cos(a), h / 2 * Math.sin(a), false]); }
    } else if (shape === 'arch') {                     // square foot, round head (h ≥ w)
      const r = w / 2, ys = h / 2 - r, N = lite ? 20 : 32;
      P.push([-w / 2, -h / 2, true], [w / 2, -h / 2, true]);
      for (let i = 0; i <= N; i++) { const a = i / N * Math.PI; P.push([r * Math.cos(a), ys + r * Math.sin(a), false]); }
    } else P.push([-w / 2, -h / 2, true], [w / 2, -h / 2, true], [w / 2, h / 2, true], [-w / 2, h / 2, true]);
    return P;
  };
  // the outline moved inward by d (a number, or d(i) per point), mitred at the corners
  const inset = (P, d) => P.map((p, i) => {
    const a = P[(i - 1 + P.length) % P.length], c = P[(i + 1) % P.length];
    const l1 = Math.hypot(p[0] - a[0], p[1] - a[1]) || 1, l2 = Math.hypot(c[0] - p[0], c[1] - p[1]) || 1;
    const n1x = (p[1] - a[1]) / l1, n1y = -(p[0] - a[0]) / l1, n2x = (c[1] - p[1]) / l2, n2y = -(c[0] - p[0]) / l2;
    let nx = n1x + n2x, ny = n1y + n2y; const l = Math.hypot(nx, ny) || 1; nx /= l; ny /= l;
    const k = (typeof d === 'function' ? d(i) : d) / Math.max(0.3, nx * n1x + ny * n1y);
    return [p[0] - nx * k, p[1] - ny * k, p[2]];
  });
  // more points along each edge (corners kept), for torn edges
  const resample = (P, step) => {
    const out = [];
    P.forEach((p, i) => {
      const c = P[(i + 1) % P.length], n = Math.max(1, Math.ceil(Math.hypot(c[0] - p[0], c[1] - p[1]) / step));
      out.push(p);
      for (let k = 1; k < n; k++) out.push([p[0] + (c[0] - p[0]) * k / n, p[1] + (c[1] - p[1]) * k / n, false]);
    });
    return out;
  };
  // a moulding profile swept round an outline: smooth along curves, creased at corners
  const sweepPath = (P, prof, mat, parent) => {
    const rings = prof.map(([d]) => inset(P, d)), m = prof.length, cols = [];
    P.forEach((p, i) => { cols.push(i); if (p[2]) cols.push(i); });          // a corner gets two columns: the mitre creases
    const pos = [], idx = [];
    for (const i of cols) for (let j = 0; j < m; j++) pos.push(rings[j][i][0], rings[j][i][1], prof[j][1]);
    for (let c = 0; c < cols.length; c++) {
      const c2 = (c + 1) % cols.length;
      if (cols[c] === cols[c2]) continue;
      const a = c * m, b = c2 * m;
      for (let j = 0; j < m - 1; j++) idx.push(a + j, b + j, a + j + 1, b + j, b + j + 1, a + j + 1);
    }
    const g2 = new THREE.BufferGeometry();
    g2.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g2.setIndex(idx); g2.computeVertexNormals();
    return add(g2, mat, 0, 0, 0, parent);
  };
  // points spaced evenly round an outline at an inset, each with its edge's direction
  const alongPath = (P, d, step, skip = () => false) => {
    const Q = inset(P, d), segs = [], out = [];
    let per = 0;
    Q.forEach((a, i) => { const c = Q[(i + 1) % Q.length], L = Math.hypot(c[0] - a[0], c[1] - a[1]); segs.push([a, c, L]); per += L; });
    const N = Math.max(4, Math.round(per / step)), st = per / N;
    let s = st / 2, acc = 0, k = 0;
    for (const [a, c, L] of segs) {
      while (s < acc + L) {
        const t = (s - acc) / L, x = a[0] + (c[0] - a[0]) * t, y = a[1] + (c[1] - a[1]) * t;
        if (!skip(x, y)) out.push([x, y, Math.atan2(c[1] - a[1], c[0] - a[0]), k]);
        k++; s += st;
      }
      acc += L;
    }
    return out;
  };
  // the cut-out canvas for any outline: dust board, centre brace, a torn ring of canvas
  const tornPath = (F, P, b, z0) => {
    const T = 0.045, open = inset(P, b);
    const ys = open.map(p => p[1]), y0 = Math.min(...ys), y1 = Math.max(...ys);
    add(new THREE.ShapeGeometry(new THREE.Shape(inset(P, b - 0.03).map(([x, y]) => new THREE.Vector2(x, y)))), DUSTBOARD, 0, 0, z0 - T - 0.004, F);
    add(rbox(0.045, y1 - y0, T * 0.8, 0.008, 1), RAWWOOD, 0, (y0 + y1) / 2, z0 - T * 0.6, F);
    // (the sight edge first, then more points along it, each torn inward by its own depth;
    // a corner tears only a little, so it never folds past its neighbours)
    const E = resample(open, 0.03), deps = E.map((q) => q[2] ? 0.01 : 0.014 + rnd() * 0.012 + (rnd() < 0.08 ? 0.02 : 0));
    const O = resample(inset(P, b - 0.02), 0.06), H = inset(E, (i) => deps[i]);
    const sh = new THREE.Shape(O.map(([x, y]) => new THREE.Vector2(x, y)));
    sh.holes.push(new THREE.Path(H.map(([x, y]) => new THREE.Vector2(x, y)).reverse()));
    const sg = new THREE.ShapeGeometry(sh), uv = sg.attributes.uv, p = sg.attributes.position;
    // the painted edge runs along the strip: u round the ring, v from the tacking margin inward
    const runs = (R) => { const s = [0]; for (let i = 1; i < R.length; i++) s.push(s[i - 1] + Math.hypot(R[i][0] - R[i - 1][0], R[i][1] - R[i - 1][1])); return s; };
    const sO = runs(O), sH = runs(H), LO = sO[sO.length - 1] || 1, LH = sH[sH.length - 1] || 1;
    const near = (R, x, y) => { let bi = 0, bd = 1e9; R.forEach((q, i) => { const d = (q[0] - x) ** 2 + (q[1] - y) ** 2; if (d < bd) { bd = d; bi = i; } }); return [bi, bd]; };
    for (let i = 0; i < uv.count; i++) {
      const x = p.getX(i), y = p.getY(i), [io, dO] = near(O, x, y), [ih, dH] = near(H, x, y);
      if (dO <= dH) uv.setXY(i, sO[io] * 3, 0.15);
      else uv.setXY(i, sH[ih] / LH * LO * 3, 0.15 + (0.02 + deps[ih]) * 12);
    }
    add(sg, RAG, 0, 0, z0 + 0.003, F);
  };
  // where carving goes on each shape: [x, y, outward angle, weight (1 = the crest)]
  const spots = (w, h, b, shape) => shape === 'oval' ? [[0, h / 2 - b * 0.45, Math.PI / 2, 1], [0, -h / 2 + b * 0.45, -Math.PI / 2, 0.6]]
    : shape === 'arch' ? [[0, h / 2 - b * 0.45, Math.PI / 2, 1], ...[-1, 1].map(sx => [sx * (w / 2 - b * 0.42), -h / 2 + b * 0.42, Math.atan2(-1, sx), 0.7])]
    : [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([sx, sy]) => [sx * (w / 2 - b * 0.42), sy * (h / 2 - b * 0.42), Math.atan2(sy, sx), 0.8]);
  const pathFrame = (F, w, h, b, style, shape, M, MH, ML) => {
    if (shape === 'arch') h = Math.max(h, w);
    const P = outline(w, h, shape);
    if (!PATH_STYLES.has(style)) style = 'corners';
    if (style === 'deep') {
      // flat outer band, a tall ogee, a deep cove in shadow, two fillets, a gilt sight bead
      const front = profile([[0, 0.02], [0.006, 0.05], [0.02, 0.058], [b * 0.18, 0.06], [b * 0.3, 0.09], [b * 0.42, 0.1], [b * 0.5, 0.078],
        [b * 0.62, 0.035], [b * 0.74, 0.03], [b * 0.8, 0.05], [b * 0.86, 0.064], [b * 0.93, 0.05], [b, 0.02]], 30);
      const i1 = front.findIndex(q => q[0] >= b * 0.5), i2 = front.findIndex(q => q[0] >= b * 0.76);
      sweepPath(P, closeLoop(front.slice(0, i1 + 1)), M, F);
      sweepPath(P, closeLoop(front.slice(i1, i2 + 1)), ML, F);
      sweepPath(P, closeLoop(front.slice(i2)), MH, F);
      for (const [x, y] of alongPath(P, b * 0.42, 0.032)) add(lobe, MH, x, y, 0.098, F).scale.setScalar(0.0075);   // a bead run on the ogee
    } else if (style === 'scallop') {
      // a rounded rim, broken into scallops past the outer edge; pearls on the sight bead
      const front = profile([[0, 0.02], [0.01, 0.06], [b * 0.25, 0.08], [b * 0.5, 0.06], [b * 0.7, 0.045], [b * 0.82, 0.06], [b * 0.92, 0.055], [b, 0.02]], 24);
      const i1 = front.findIndex(q => q[0] >= b * 0.76);
      sweepPath(P, closeLoop(front.slice(0, i1 + 1)), M, F);
      sweepPath(P, closeLoop(front.slice(i1)), MH, F);
      for (const [x, y, ang, k] of alongPath(P, b * 0.06, b * 0.62)) {
        const s = add(lobe, k % 2 ? M : MH, x, y, 0.045, F);
        s.scale.set(b * 0.34, b * 0.24, 0.035); s.rotation.z = ang;
      }
      for (const [x, y] of alongPath(P, b * 0.82, 0.03)) add(lobe, MH, x, y, 0.06, F).scale.setScalar(0.0075);
      for (const [x, y] of spots(w, h, b, shape)) {          // a rosette at each corner / the crest
        for (let k = 0; k < 6; k++) { const a = k / 6 * Math.PI * 2; const q = add(lobe, MH, x + Math.cos(a) * b * 0.16, y + Math.sin(a) * b * 0.16, 0.085, F); q.scale.set(b * 0.14, b * 0.07, 0.014); q.rotation.z = a; }
        add(lobe, ML, x, y, 0.09, F).scale.set(b * 0.1, b * 0.1, 0.018);
      }
    } else {
      // a plain moulding with a gilt sight bead, carved where the shape wants it
      const front = profile([[0, 0.02], [0.008, 0.055], [b * 0.15, 0.066], [b * 0.55, 0.05], [b * 0.8, 0.055], [b * 0.88, 0.07], [b * 0.95, 0.055], [b, 0.02]], 22);
      const i1 = front.findIndex(q => q[0] >= b * 0.78);
      sweepPath(P, closeLoop(front.slice(0, i1 + 1)), M, F);
      sweepPath(P, closeLoop(front.slice(i1)), MH, F);
      for (const [x, y, out, wt] of spots(w, h, b, shape)) {
        const R = b * (0.42 + 0.25 * wt);
        shell(F, x + Math.cos(out) * b * 0.05, y + Math.sin(out) * b * 0.05, 0.08, out, R, wt > 0.9 ? 9 : 7, MH, M);
        for (const s2 of [-1, 1]) {
          leaf(F, x, y, 0.075, out + s2 * (wt > 0.9 ? 1.9 : 2.3), b * (0.55 + 0.4 * wt), M, 0.18);
          if (wt > 0.9) cscroll(F, x + Math.cos(out + s2 * 1.3) * R * 0.75, y + Math.sin(out + s2 * 1.3) * R * 0.75, 0.085, out + s2 * 1.1, b * 0.13, MH, s2 < 0);
        }
      }
    }
    emptiedPath(F, P, b, 0.012);
    return F;
  };
  // a painting in the sight opening (the portfolio): the canvas a little behind the sight
  // edge, its picture fitted to the opening, the dust board behind so the back reads solid
  const hung = (F, pts, z0, art) => {
    const sh = new THREE.Shape(pts.map(([x, y]) => new THREE.Vector2(x, y)));
    const geo = new THREE.ShapeGeometry(sh, 24), p = geo.attributes.position, uv = geo.attributes.uv;
    const xs = pts.map(q => q[0]), ys = pts.map(q => q[1]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    for (let i = 0; i < p.count; i++) uv.setXY(i, (p.getX(i) - x0) / (x1 - x0), (p.getY(i) - y0) / (y1 - y0));
    const mat = new THREE.MeshBasicMaterial({ map: art, toneMapped: false });
    const m = add(geo, mat, 0, 0, z0, F);
    m.userData.noInk = true; m.userData.painting = true;
    add(new THREE.ShapeGeometry(sh), DUSTBOARD, 0, 0, z0 - 0.03, F).rotation.y = Math.PI;
    F.userData.canvas = m;
    return m;
  };
  const ornateFrame = (w, h, parent, style = 'baroque', { shape = 'rect', finish = 'gold', art = null } = {}) => {
    const F = new THREE.Group(); parent.add(F);
    if (art) {                                         // (no torn canvas: the picture fills the opening)
      emptied = (F2, ow, oh, z0) => hung(F2, [[-ow / 2 - 0.02, -oh / 2 - 0.02], [ow / 2 + 0.02, -oh / 2 - 0.02], [ow / 2 + 0.02, oh / 2 + 0.02], [-ow / 2 - 0.02, oh / 2 + 0.02]], z0, art);
      emptiedPath = (F2, P, b, z0) => hung(F2, inset(P, b - 0.02), z0, art);
    } else { emptied = tornRect; emptiedPath = tornPath; }
    const b = Math.min(w, h) * 0.18;                                   // the moulding's width
    const ow = w - 2 * b, oh = h - 2 * b;                              // the sight opening
    const [M, MH, ML] = finishMats(finish);
    if (shape !== 'rect' || PATH_STYLES.has(style)) return pathFrame(F, w, h, b, style, shape, M, MH, ML);
    if (style === 'walnut') {
      // a bold reverse profile in walnut: outer roll, a deep scotia, a carved flat, then the gilt slip
      const front = profile([[0, 0.02], [0.012, 0.075], [0.035, 0.09], [b * 0.38, 0.05], [b * 0.62, 0.065], [b * 0.8, 0.07], [b * 0.84, 0.045]]);
      sweep(w, h, closeLoop(front), WALNUT, F);
      sweep(w, h, closeLoop(profile([[b * 0.84, 0.045], [b * 0.9, 0.065], [b * 0.97, 0.055], [b, 0.02]], 8), 0.0), GOLD, F);   // the gilt slip
      // leaf-and-dart carved round the outer roll
      for (const [x, y, ang, k] of alongSides(w, h, 0.03, 0.045)) {
        const m = add(lobe, WALNUT_HI, x, y, 0.086, F);                                       // a pointed leaf, then a dart
        if (k % 2) { m.scale.set(0.007, 0.02, 0.008); m.rotation.z = ang; } else m.scale.setScalar(0.006);
      }
      // carved acanthus in each corner, a gilt rosette at its heart
      for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
        const cx = sx * (w / 2 - b * 0.45), cy = sy * (h / 2 - b * 0.45), out = Math.atan2(sy, sx);
        for (const da of [-2.35, 2.35]) leaf(F, cx, cy, 0.07, out + da, b * 0.62, WALNUT_HI, 0.15);
        leaf(F, cx, cy, 0.075, out, b * 0.45, WALNUT_HI, 0.3);
        add(lobe, GOLD_HI, cx, cy, 0.09, F).scale.set(b * 0.13, b * 0.13, b * 0.09);
      }
      emptied(F, ow, oh, 0.01);
      return F;
    }
    if (style === 'fluted') {
      // a wide gilt band carved into flutes (the grooves ARE the profile, so they mitre at the corners)
      const pts = [[0, 0.03], [0.008, 0.068], [0.02, 0.075]], FL = 6, fw = (b * 0.8 - 0.02) / FL;
      for (let k = 0; k < FL; k++) for (let j = 1; j <= 6; j++) { const t = j / 6; pts.push([0.02 + k * fw + t * fw, 0.075 - 0.018 * Math.sin(Math.PI * t)]); }
      pts.push([b * 0.84, 0.07], [b * 0.86, 0.045]);
      sweep(w, h, closeLoop(pts), M, F);
      sweep(w, h, closeLoop(profile([[b * 0.86, 0.045], [b * 0.92, 0.075], [b * 0.98, 0.06], [b, 0.02]], 8), 0.0), MH, F);
      // ribbon-and-stick on the sight bead: a twist of short ribbons, then a stick
      for (const [x, y, ang, k] of alongSides(w, h, b * 0.92, 0.03)) {
        const m = add(lobe, k % 3 ? MH : ML, x, y, 0.078, F);
        if (k % 3) { m.scale.set(0.011, 0.006, 0.006); m.rotation.z = ang + (k % 3 === 1 ? 0.6 : -0.6); }
        else m.scale.set(0.004, 0.004, 0.006);
      }
      // the corners: a square block with a carved rosette
      for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
        const cx = sx * (w / 2 - b * 0.43), cy = sy * (h / 2 - b * 0.43);
        add(rbox(b * 0.86, b * 0.86, 0.03, 0.01, 1), M, cx, cy, 0.075, F);
        for (let k = 0; k < 8; k++) { const a = k / 8 * Math.PI * 2; const p = add(lobe, k % 2 ? ML : MH, cx + Math.cos(a) * b * 0.2, cy + Math.sin(a) * b * 0.2, 0.095, F); p.scale.set(b * 0.16, b * 0.07, 0.012); p.rotation.z = a; }
        add(lobe, MH, cx, cy, 0.1, F).scale.set(b * 0.12, b * 0.12, 0.02);
      }
      emptied(F, ow, oh, 0.01);
      return F;
    }
    // Louis XV gilt: outer bead, a swelling top ogee, a deep cove, a raised sight bead
    const front = profile([[0, 0.025], [0.01, 0.06], [0.025, 0.07], [b * 0.32, 0.105], [b * 0.5, 0.085], [b * 0.66, 0.05], [b * 0.8, 0.055], [b * 0.88, 0.075], [b * 0.95, 0.06], [b, 0.025]], 26);
    const iOg = front.findIndex(p => p[0] >= b * 0.5), iCove = front.findIndex(p => p[0] >= b * 0.8);
    sweep(w, h, closeLoop(front.slice(0, iOg + 1)), M, F);                                  // bead + ogee
    sweep(w, h, closeLoop(front.slice(iOg, iCove + 1)), ML, F);                           // the cove
    sweep(w, h, closeLoop(front.slice(iCove)), MH, F);                                    // the sight bead
    const nearOrn = (x, y, r) => (Math.abs(Math.abs(x) - (w / 2 - b * 0.42)) < r && Math.abs(Math.abs(y) - (h / 2 - b * 0.42)) < r) || Math.abs(x) < r * 0.9 || Math.abs(y) < r * 0.9;
    // egg-and-dart along the top of the ogee
    for (const [x, y, ang, k] of alongSides(w, h, b * 0.32, 0.042, (x, y) => nearOrn(x, y, b * 0.75))) {
      const e = add(lobe, k % 2 ? MH : ML, x, y, 0.104, F);
      if (k % 2) e.scale.set(0.016, 0.011, 0.01); else e.scale.set(0.003, 0.012, 0.006);
      e.rotation.z = ang;
    }
    // pearls on the sight bead
    const pearl = new THREE.SphereGeometry(1, 6, 4);
    for (const [x, y] of alongSides(w, h, b * 0.88, 0.028)) add(pearl, MH, x, y, 0.078, F).scale.setScalar(0.0085);
    // rocaille corners: a shell, acanthus sweeping along both sides and breaking past the outer
    // edge, two C-scrolls: the swirl that makes a frame read as Louis XV
    for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
      const cx = sx * (w / 2 - b * 0.42), cy = sy * (h / 2 - b * 0.42), out = Math.atan2(sy, sx);
      shell(F, cx + Math.cos(out) * b * 0.06, cy + Math.sin(out) * b * 0.06, 0.11, out, b * 0.5, 7, MH, M);
      for (const s2 of [-1, 1]) {
        leaf(F, cx, cy, 0.1, out + s2 * 2.3, b * 0.8, M, 0.18);
        leaf(F, cx + Math.cos(out + s2 * 2.3) * b * 0.5, cy + Math.sin(out + s2 * 2.3) * b * 0.5, 0.098, out + s2 * 2.55, b * 0.45, MH, 0.25);
        cscroll(F, cx + Math.cos(out + s2 * 1.4) * b * 0.32, cy + Math.sin(out + s2 * 1.4) * b * 0.32, 0.11, out + s2 * 1.2, b * 0.13, MH, s2 < 0);
      }
    }
    // a centre cartouche on each side: a smaller shell flanked by scrolls and leaves
    for (const [x, y, out] of [[0, -h / 2 + b * 0.42, -Math.PI / 2], [0, h / 2 - b * 0.42, Math.PI / 2], [w / 2 - b * 0.42, 0, 0], [-w / 2 + b * 0.42, 0, Math.PI]]) {
      shell(F, x, y, 0.11, out, b * 0.4, 5, MH, M);
      for (const s2 of [-1, 1]) {
        cscroll(F, x + Math.cos(out + s2 * 1.57) * b * 0.36, y + Math.sin(out + s2 * 1.57) * b * 0.36, 0.105, out + s2 * 0.4, b * 0.12, MH, s2 < 0);
        leaf(F, x + Math.cos(out + s2 * 1.57) * b * 0.15, y + Math.sin(out + s2 * 1.57) * b * 0.15, 0.1, out + s2 * 1.7, b * 0.6, M, 0.2);
      }
    }
    emptied(F, ow, oh, 0.012);
    return F;
  };
  return { ornateFrame };
}
