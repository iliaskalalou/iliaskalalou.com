/* ============================================================================
   HERO — Mount Fuji / Chureito pagoda / portrait / momiji, as one real 3D
   scene: one PerspectiveCamera, four meshes carrying the geometry that was
   modelled in Blender, and a leaf system that lives in the same world space.

   The camera moves on pointer. Nothing is a flat layer, so the pagoda turns,
   the tree's cards separate in depth, Fuji's rim light slides along its ridge,
   and leaves pass BEHIND the tree and IN FRONT of the portrait because that is
   where they actually are.
   ============================================================================ */
import {
  Scene, PerspectiveCamera, WebGLRenderer, Group, Mesh, MeshStandardMaterial,
  ShaderMaterial, PlaneGeometry, InstancedBufferGeometry, InstancedBufferAttribute,
  BufferAttribute, DirectionalLight, HemisphereLight, AmbientLight, Color, Vector3,
  Vector2, Box3, TextureLoader, CanvasTexture, SRGBColorSpace, NoToneMapping, DoubleSide,
  NormalBlending, MathUtils, Fog
} from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import * as L from './leaves.js';

/* ------------------------------------------------------------------- palette
   Straight off the site's tokens. Everything warm in the scene is one of
   these two; everything cool is the shadow colour. */
const EMBER = 0xC1440E;
const AMBER = 0xE08D3C;
const BG    = 0x0c0c0c;

/* Baked into the Fuji vertex colours by tools/export_fuji.py — the body colour
   was renormalised to fill 0..1 so 8-bit quantisation would not band it. */
const BODY_SCALE = 0.019155;

/* ------------------------------------------------------------------- layout
   Real depths, in metres-ish. The whole point of the exercise: these are
   distances, not z-index. Depth is compressed relative to the real world (a
   real Fuji is 20 km away, not 300) so that the pointer parallax has anything
   at all to show on the mountain; everything nearer is honest.            */
/* Fuji's geometry is stretched vertically once, at load. The blend is a
   stylised flat cone shot on a 220 mm lens; at a hero lens its peak would sit
   barely above the horizon. Art direction, stated plainly rather than hidden. */
const FUJI_STRETCH = 2.6;

const LANDSCAPE = {
  fov: 33,
  fuji:     { z: -380, x: -34.0, y: -95.0, s: 19.0, ry: 0.10 },
  pagoda:   { z:  -60, x: -18.8, y: -13.9, s: 3.42, ry: 0.34 },
  portrait: { z:  -22, x:  -0.6, y:   0.3, h: 6.25 },
  tree:     { z:  -20, x:   8.6, y:  -7.1, s: 1.38, ry: 0.03 },
  leafNear: -11.5,
  leafFar:  -46.0
};

/* A portrait viewport is not the same picture cropped -- a perspective camera
   loses HORIZONTAL field as the frame narrows, and at 390x844 the pagoda and
   the momiji both fall off the sides. So the phone gets its own staging:
   everything pulled in toward the axis, Fuji brought much closer and smaller
   so its flanks still resolve. Same geometry, same camera, restaged. */
const PORTRAIT = {
  fov: 42,
  fuji:     { z: -260, x: -12.0, y:  -9.3, s: 8.5, ry: 0.10 },
  pagoda:   { z:  -60, x:  -6.6, y: -16.0, s: 2.60, ry: 0.34 },
  portrait: { z:  -22, x:  -0.5, y:   1.4, h: 5.50 },
  tree:     { z:  -20, x:   7.6, y:  -9.2, s: 1.66, ry: 0.03 },
  leafNear: -11.5,
  leafFar:  -46.0
};

let LAYOUT = LANDSCAPE;

/* =========================================================== boot / fallback */
const canvas = document.getElementById('gl');
const panel = document.getElementById('panel');

function fail(msg) {
  document.getElementById('fallback').hidden = false;
  document.getElementById('fallback-msg').textContent = msg;
  canvas.hidden = true;
}

let gl = null;
try { gl = canvas.getContext('webgl2', { antialias: true, alpha: false, powerPreference: 'high-performance' }); }
catch (e) { gl = null; }
if (!gl) {
  fail('WebGL 2 is unavailable here, so the 3D scene cannot run. This is a still frame of it.');
  throw new Error('no webgl2');
}

const renderer = new WebGLRenderer({ canvas, context: gl, antialias: true, alpha: false });
renderer.setClearColor(BG, 1);
renderer.outputColorSpace = SRGBColorSpace;
/* Blender rendered fuji_final.png and tree_final.png with view_transform
   'Standard' -- a straight linear->sRGB encode, no filmic curve. Reproducing
   that exactly means NO tone mapping here; the baked vertex colours then land
   on screen at the values the original renders have. (The pagoda blend used
   AgX, but the pagoda is relit by real lights in this scene anyway, so its
   intensities were matched by eye against pagoda_final.png instead.) */
renderer.toneMapping = NoToneMapping;

const DPR_CAP = 1.5;
const scene = new Scene();
scene.background = new Color(BG);
scene.fog = new Fog(BG, 34, 190);           // pagoda sinks into it; Fuji opts out

const camera = new PerspectiveCamera(LANDSCAPE.fov, 1, 0.4, 1200);
camera.position.set(0, 0, 0);

/* the camera's REST pose. Leaf projection and the parallax offsets are both
   measured from here, never from the live camera, or the leaves would swim
   when the pointer moved. */
const REST = new Vector3(0, 0, 0);

/* ---------------------------------------------------------------- lighting
   Warm key from the RIGHT (behind the momiji, the direction the sun has just
   left), deep cool fill from the left, and almost no ambient — the page is
   #0c0c0c and the scene has to stay in that hole. */
const key = new DirectionalLight(new Color(AMBER), 3.10);
key.position.set(9, 3.2, -4).normalize();
scene.add(key);

const rim = new DirectionalLight(new Color(EMBER), 2.10);
rim.position.set(4, 5.5, -12).normalize();
scene.add(rim);

const fill = new DirectionalLight(new Color(0x2a3d63), 0.9);
fill.position.set(-10, 1.5, 5).normalize();
scene.add(fill);

scene.add(new HemisphereLight(0x1b2436, 0x050505, 0.35));
scene.add(new AmbientLight(0xffffff, 0.035));

/* ============================================================ asset loading */
const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
const texLoader = new TextureLoader();

function loadGLB(url) {
  return new Promise((res, rej) => loader.load(url, g => {
    let mesh = null;
    g.scene.traverse(o => { if (o.isMesh && !mesh) mesh = o; });
    if (!mesh) return rej(new Error('no mesh in ' + url));
    mesh.updateWorldMatrix(true, false);
    const geo = mesh.geometry;
    /* KHR_mesh_quantization stores positions as raw uint16 and puts the
       scale/offset on the node. applyMatrix4 would write floats straight back
       into that uint16 storage and shred the mesh, so dequantise first. */
    const p = geo.getAttribute('position');
    if (!(p.array instanceof Float32Array)) {
      // read through getX/getY/getZ, never the raw array: meshopt pads a
      // uint16 VEC3 to a 8-byte stride, so raw indexing walks into padding
      const f = new Float32Array(p.count * 3);
      for (let i = 0; i < p.count; i++) {
        f[i * 3] = p.getX(i); f[i * 3 + 1] = p.getY(i); f[i * 3 + 2] = p.getZ(i);
      }
      geo.setAttribute('position', new BufferAttribute(f, 3));
    }
    geo.applyMatrix4(mesh.matrixWorld);             // bake gltfpack's node transform
    res(geo);
  }, undefined, rej));
}
function loadTex(url, srgb) {
  return new Promise((res, rej) => texLoader.load(url, t => {
    if (srgb) t.colorSpace = SRGBColorSpace;
    t.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
    res(t);
  }, undefined, rej));
}

/* gltfpack keeps our two colour sets as COLOR_1 / COLOR_2 (COLOR_0 is the
   exporter's redundant 8-bit copy and gets dropped). Normalise the names. */
function fixColors(geo) {
  if (!geo.getAttribute('color') && geo.getAttribute('color_1')) {
    geo.setAttribute('color', geo.getAttribute('color_1'));
  }
  return geo;
}

/* =============================================================== the scene */
const world = new Group();          // everything that parallaxes together
scene.add(world);

let treeGroup = null, leafMesh = null;
const parts = {};

const READY = Promise.all([
  loadGLB('assets/fuji.glb'),
  loadGLB('assets/pagoda.glb'),
  loadGLB('assets/branches.glb'),
  loadGLB('assets/foliage.glb'),
  loadTex('assets/leaf_atlas.webp', true),
  loadTex('assets/sprite_atlas.webp', true)
]).then(([gFuji, gPag, gBark, gFol, texLeaf, texSprite]) => {

  /* ---------------------------------------------------------------- FUJI
     Two vertex-colour sets came out of the original build script:
       COLOR_1  rgb = body colour (renormalised), a = haze ramp
       COLOR_2  r = warm rim mask, g = snow, b = cool counter-rim
     The rim terms are Fresnel and therefore VIEW DEPENDENT. Baked into a PNG
     they would be frozen; here they move as the camera moves.               */
  gFuji.scale(1, FUJI_STRETCH, 1);                      // vertical stretch, then
  gFuji.computeVertexNormals();  // normals recomputed here (not shipped: -12 B/vtx)
  const fuji = new Mesh(gFuji, new ShaderMaterial({
    transparent: true, depthWrite: false, fog: false,
    uniforms: {
      uBodyScale: { value: BODY_SCALE },
      uRim:       { value: new Color(0xd68544).convertSRGBToLinear() },
      uRimCool:   { value: new Color(0x4a5c7c).convertSRGBToLinear() },
      uRimGain:   { value: 2.6 },
      uCoolGain:  { value: 0.85 },
      uLift:      { value: 1.45 }
    },
    vertexShader: `
      attribute vec4 color_1;
      attribute vec4 color_2;
      varying vec4 vBody; varying vec4 vMask; varying vec3 vN; varying vec3 vI;
      void main(){
        vBody = color_1; vMask = color_2;
        vec4 wp = modelMatrix * vec4(position,1.0);
        vN = normalize(mat3(modelMatrix) * normal);
        vI = normalize(cameraPosition - wp.xyz);
        gl_Position = projectionMatrix * viewMatrix * wp;
      }`,
    fragmentShader: `
      uniform float uBodyScale, uRimGain, uCoolGain, uLift;
      uniform vec3 uRim, uRimCool;
      varying vec4 vBody; varying vec4 vMask; varying vec3 vN; varying vec3 vI;
      void main(){
        float f = clamp(1.0 - dot(normalize(vN), normalize(vI)), 0.0, 1.0);
        vec3 body = vBody.rgb * uBodyScale * uLift;
        vec3 warm = uRim     * pow(f, 9.0) * vMask.r * uRimGain;
        vec3 cool = uRimCool * pow(f, 5.0) * vMask.b * uCoolGain;
        gl_FragColor = vec4(body + warm + cool, vBody.a);
        #include <colorspace_fragment>
      }`
  }));
  fuji.renderOrder = -20;
  place(fuji, LAYOUT.fuji);
  world.add(fuji);
  parts.fuji = fuji;

  /* -------------------------------------------------------------- PAGODA
     Nine flat Blender materials baked to one vertex-colour set, one draw
     call, flat-shaded from screen-space derivatives (no normals shipped). */
  fixColors(gPag);
  const pagoda = new Mesh(gPag, new MeshStandardMaterial({
    vertexColors: true, flatShading: true, roughness: 0.72, metalness: 0.0,
    side: DoubleSide
  }));
  place(pagoda, LAYOUT.pagoda);
  world.add(pagoda);
  parts.pagoda = pagoda;

  /* ----------------------------------------------------------- THE MOMIJI */
  treeGroup = new Group();
  place(treeGroup, LAYOUT.tree);
  world.add(treeGroup);
  parts.tree = treeGroup;

  gBark.computeVertexNormals();
  const bark = new Mesh(gBark, new MeshStandardMaterial({
    color: new Color(0x1d1512), roughness: 0.86, metalness: 0.0,
    emissive: new Color(0x2a1608), emissiveIntensity: 0.30
  }));
  treeGroup.add(bark);

  /* 120 alpha cards, ONE mesh, ONE alpha-tested draw call. Alpha test rather
     than blending: it writes depth, so falling leaves and the portrait sort
     against the canopy correctly and the cards do not fight each other. */
  fixColors(gFol);
  /* glTF UV origin is the TOP-left of the image; three's TextureLoader
     defaults to flipY = true, which puts it at the bottom-left. */
  texLeaf.flipY = false;
  const foliage = new Mesh(gFol, new ShaderMaterial({
    transparent: false, alphaTest: 0.42, side: DoubleSide, toneMapped: false,
    uniforms: {
      map:    { value: texLeaf },
      uEmit:  { value: 0.42 },
      uAmb:   { value: 0.20 },
      uKey:   { value: new Color(AMBER).convertSRGBToLinear() }
    },
    vertexShader: `
      attribute vec4 color_1;
      varying vec2 vUv; varying vec4 vCol;
      void main(){
        vUv = uv; vCol = color_1;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0);
      }`,
    fragmentShader: `
      uniform sampler2D map; uniform float uEmit, uAmb; uniform vec3 uKey;
      varying vec2 vUv; varying vec4 vCol;
      void main(){
        vec4 t = texture2D(map, vUv);
        if (t.a < 0.42) discard;
        // vCol.a carries the per-card backlight strength (0..3, stored /3)
        float e = vCol.a * 3.0 * uEmit;
        vec3 c = t.rgb * vCol.rgb * (uAmb + e) * mix(vec3(1.0), uKey, 0.35);
        gl_FragColor = vec4(c, 1.0);
        #include <colorspace_fragment>
      }`
  }));
  foliage.material.alphaTest = 0.42;
  treeGroup.add(foliage);

  /* ------------------------------------------------------------- PORTRAIT
     PLACEHOLDER. The owner has not sent his photograph. This is a canvas
     texture generated at runtime — it costs zero bytes over the wire and it
     is meant to look like the stand-in that it is. */
  const portrait = new Mesh(
    new PlaneGeometry(LAYOUT.portrait.h * 0.8, LAYOUT.portrait.h),
    new ShaderMaterial({
      transparent: true, depthWrite: true, alphaTest: 0.02, fog: false,
      toneMapped: false,
      uniforms: { map: { value: makePortrait() } },
      vertexShader: `varying vec2 vUv; void main(){ vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
      fragmentShader: `uniform sampler2D map; varying vec2 vUv;
        void main(){ vec4 t = texture2D(map, vUv); if(t.a<0.02) discard;
          gl_FragColor = t;
          #include <colorspace_fragment>
        }`
    })
  );
  portrait.position.set(LAYOUT.portrait.x, LAYOUT.portrait.y, LAYOUT.portrait.z);
  world.add(portrait);
  parts.portrait = portrait;
  parts.bark = bark; parts.foliage = foliage;

  /* ----------------------------------------------------------- THE LEAVES */
  leafMesh = makeLeafMesh(texSprite);
  world.add(leafMesh);
  parts.leaves = leafMesh;

  return true;
});

function restage() {
  if (!parts.fuji) return;
  place(parts.fuji, LAYOUT.fuji);
  place(parts.pagoda, LAYOUT.pagoda);
  place(parts.tree, LAYOUT.tree);
  parts.portrait.position.set(LAYOUT.portrait.x, LAYOUT.portrait.y, LAYOUT.portrait.z);
  parts.portrait.geometry.dispose();
  parts.portrait.geometry = new PlaneGeometry(LAYOUT.portrait.h * 0.8, LAYOUT.portrait.h);
}

function place(obj, p) {
  obj.position.set(p.x, p.y, p.z);
  if (p.s) obj.scale.set(p.s, p.sy != null ? p.sy : p.s, p.s);
  obj.rotation.y = p.ry || 0;
}

/* ------------------------------------------------- portrait placeholder art */
function makePortrait() {
  const W = 512, H = 640, R = 26;
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const x = c.getContext('2d');
  const r = (px, py, w, h, rad) => {
    x.beginPath();
    x.moveTo(px + rad, py);
    x.arcTo(px + w, py, px + w, py + h, rad);
    x.arcTo(px + w, py + h, px, py + h, rad);
    x.arcTo(px, py + h, px, py, rad);
    x.arcTo(px, py, px + w, py, rad);
    x.closePath();
  };
  r(0, 0, W, H, R);
  const g = x.createLinearGradient(0, 0, W * 0.55, H);
  g.addColorStop(0, '#121211');
  g.addColorStop(0.55, '#0d0d0c');
  g.addColorStop(1, '#080807');
  x.fillStyle = g; x.fill();

  x.save(); x.clip();
  const v = x.createRadialGradient(W * 0.5, H * 0.42, W * 0.15, W * 0.5, H * 0.5, W * 0.85);
  v.addColorStop(0, 'rgba(224,141,60,0.030)');
  v.addColorStop(1, 'rgba(0,0,0,0.62)');
  x.fillStyle = v; x.fillRect(0, 0, W, H);
  x.restore();

  r(1, 1, W - 2, H - 2, R - 1);
  x.strokeStyle = 'rgba(237,237,237,0.085)'; x.lineWidth = 2; x.stroke();

  x.fillStyle = 'rgba(237,237,237,0.155)';
  x.textAlign = 'center'; x.textBaseline = 'middle';
  x.font = '300 190px ui-sans-serif, -apple-system, Helvetica, Arial, sans-serif';
  x.fillText('IK', W / 2, H * 0.47);
  x.fillStyle = 'rgba(143,143,143,0.42)';
  x.font = '500 20px ui-monospace, SFMono-Regular, Menlo, monospace';
  x.letterSpacing = '3px';
  x.fillText('PORTRAIT · PLACEHOLDER', W / 2, H * 0.75);

  const t = new CanvasTexture(c);
  t.colorSpace = SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

/* ================================================================== LEAVES */
const NL = L.CFG.MAX_LEAVES;
const aPos   = new Float32Array(NL * 3);
const aRot   = new Float32Array(NL);
const aSize  = new Float32Array(NL);
const aAlpha = new Float32Array(NL);
const aCell  = new Float32Array(NL);
const aFlip  = new Float32Array(NL);
let attrPos, attrRot, attrSize, attrAlpha, attrCell, attrFlip, leafGeo;

function makeLeafMesh(tex) {
  tex.flipY = false;
  leafGeo = new InstancedBufferGeometry();
  leafGeo.setAttribute('position', new BufferAttribute(new Float32Array([
    -0.5, -0.5, 0, 0.5, -0.5, 0, 0.5, 0.5, 0, -0.5, 0.5, 0]), 3));
  leafGeo.setAttribute('uv', new BufferAttribute(new Float32Array([
    0, 0, 1, 0, 1, 1, 0, 1]), 2));
  leafGeo.setIndex([0, 1, 2, 0, 2, 3]);

  attrPos   = new InstancedBufferAttribute(aPos, 3);   attrPos.setUsage(35048);
  attrRot   = new InstancedBufferAttribute(aRot, 1);   attrRot.setUsage(35048);
  attrSize  = new InstancedBufferAttribute(aSize, 1);  attrSize.setUsage(35048);
  attrAlpha = new InstancedBufferAttribute(aAlpha, 1); attrAlpha.setUsage(35048);
  attrCell  = new InstancedBufferAttribute(aCell, 1);  attrCell.setUsage(35048);
  attrFlip  = new InstancedBufferAttribute(aFlip, 1);  attrFlip.setUsage(35048);
  leafGeo.setAttribute('iPos', attrPos);
  leafGeo.setAttribute('iRot', attrRot);
  leafGeo.setAttribute('iSize', attrSize);
  leafGeo.setAttribute('iAlpha', attrAlpha);
  leafGeo.setAttribute('iCell', attrCell);
  leafGeo.setAttribute('iFlip', attrFlip);
  leafGeo.instanceCount = 0;

  const mat = new ShaderMaterial({
    transparent: true, depthTest: true, depthWrite: false,
    blending: NormalBlending, toneMapped: false, fog: false,
    uniforms: {
      map:    { value: tex },
      uGrid:  { value: new Vector2(8, 6) },
      uFogNear: { value: 60.0 },
      uFogFar:  { value: 210.0 }
    },
    vertexShader: `
      attribute vec3 iPos; attribute float iRot, iSize, iAlpha, iCell, iFlip;
      uniform vec2 uGrid;
      varying vec2 vUv; varying float vA;
      void main(){
        // camera-facing billboard, built from the view matrix basis, then
        // spun in its own plane by the tumble-driven heading iRot
        vec3 right = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
        vec3 up    = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
        float c = cos(iRot), s = sin(iRot);
        vec2 q = position.xy * iSize;
        q.x *= iFlip;
        vec2 rq = vec2(q.x * c - q.y * s, q.x * s + q.y * c);
        vec3 wp = iPos + right * rq.x + up * rq.y;

        float cell = iCell;
        float col = mod(cell, uGrid.x);
        float row = floor(cell / uGrid.x);
        // flipY is off on this texture, so v runs top-down like the atlas rows
        vUv = vec2(col + position.x + 0.5, row + 0.5 - position.y) / uGrid;
        vA = iAlpha;
        gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
      }`,
    fragmentShader: `
      uniform sampler2D map;
      varying vec2 vUv; varying float vA;
      void main(){
        vec4 t = texture2D(map, vUv);
        if (t.a * vA < 0.004) discard;
        gl_FragColor = vec4(t.rgb, t.a * vA);
        #include <colorspace_fragment>
      }`
  });
  const m = new Mesh(leafGeo, mat);
  m.frustumCulled = false;
  m.renderOrder = 10;
  return m;
}

/* Projection constants, refreshed on resize: they turn the leaf system's
   normalised (u, v) and drawn size into world space at a chosen depth. */
let projTan = 0, projAspect = 1, projRef = 1, projH = 1;

function syncLeaves() {
  if (!leafMesh) return;
  const n = L.getActiveCount();
  const idx = L.activeIdx;
  const nearZ = LAYOUT.leafNear, farZ = LAYOUT.leafFar;
  const pl = L.CFG.PAR_LO, ph = L.CFG.PAR_HI;
  const sizeK = 2 * projRef * projTan / projH;
  let w = 0;

  // fill in band order (far -> near): a 3-bucket approximation of a
  // back-to-front sort, which is what the 2D system did as well
  for (let band = 0; band < 3; band++) {
    for (let s = 0; s < n; s++) {
      const i = idx[s];
      if (L.pBand[i] !== band) continue;
      const a = L.drawAlpha(i);
      if (a <= 0.004) continue;

      const t = (L.pPar[i] - pl) / (ph - pl);          // 0 far .. 1 near
      const z = farZ + (nearZ - farZ) * t;
      const az = -z;
      aPos[w * 3]     = (L.pX[i] - 0.5) * 2 * projTan * projAspect * az;
      aPos[w * 3 + 1] = -(L.pY[i] - 0.5) * 2 * projTan * az;
      aPos[w * 3 + 2] = z;
      aRot[w]   = L.pTheta[i];
      aSize[w]  = L.pSize[i] * sizeK * az;
      aAlpha[w] = a;
      aCell[w]  = L.pSheet[i] * 16 + L.frameOf(i);
      aFlip[w]  = L.pFlip[i];
      w++;
    }
  }
  leafGeo.instanceCount = w;
  if (w > 0) {
    attrPos.addUpdateRange(0, w * 3); attrPos.needsUpdate = true;
    attrRot.addUpdateRange(0, w);     attrRot.needsUpdate = true;
    attrSize.addUpdateRange(0, w);    attrSize.needsUpdate = true;
    attrAlpha.addUpdateRange(0, w);   attrAlpha.needsUpdate = true;
    attrCell.addUpdateRange(0, w);    attrCell.needsUpdate = true;
    attrFlip.addUpdateRange(0, w);    attrFlip.needsUpdate = true;
  }
}

/* ================================================================== resize */
let VW = 1, VH = 1;
function resize() {
  VW = window.innerWidth || 1280;
  VH = window.innerHeight || 800;
  const dpr = Math.min(window.devicePixelRatio || 1, DPR_CAP);
  renderer.setPixelRatio(dpr);
  renderer.setSize(VW, VH, false);
  camera.aspect = VW / VH;

  const a = VW / VH;
  const want = a < 0.95 ? PORTRAIT : LANDSCAPE;
  if (want !== LAYOUT) { LAYOUT = want; restage(); }
  /* Between the two stagings, still widen the vertical FOV a little as the
     frame narrows -- the 3D equivalent of `object-fit: cover` re-framing. */
  camera.fov = LAYOUT.fov * MathUtils.clamp(
      (LAYOUT === LANDSCAPE ? 1.35 : 0.62) / a, 1.0, 1.30);
  camera.updateProjectionMatrix();

  projTan = Math.tan(MathUtils.degToRad(camera.fov) * 0.5);
  projAspect = a;
  projRef = Math.sqrt(VW * VH);
  projH = VH;

  const el = document.getElementById('v-vp');
  if (el) el.textContent = VW + '×' + VH + ' @' + dpr;
}

/* ================================================================ parallax */
const ptr = new Vector2(0, 0);        // -1 .. 1
const ptrEase = new Vector2(0, 0);
let hasPointer = false;

window.addEventListener('pointermove', e => {
  if (e.pointerType === 'touch') return;
  hasPointer = true;
  ptr.set((e.clientX / VW) * 2 - 1, (e.clientY / VH) * 2 - 1);
}, { passive: true });
window.addEventListener('pointerleave', () => { ptr.set(0, 0); }, { passive: true });

/* Small. A portfolio, not a fairground: 0.55 world units of dolly and a
   0.9-degree yaw at the extremes. On a 20-unit subject that is about 12 px of
   relative shift between the tree and the portrait — enough to feel solid,
   not enough to notice as an effect. */
const PAR_X = 0.62, PAR_Y = 0.30, PAR_YAW = 0.016, PAR_PITCH = 0.008;

function updateCamera(dt) {
  const k = 1 - Math.exp(-dt / 0.28);
  ptrEase.x += (ptr.x - ptrEase.x) * k;
  ptrEase.y += (ptr.y - ptrEase.y) * k;
  camera.position.set(REST.x + ptrEase.x * PAR_X, REST.y - ptrEase.y * PAR_Y, REST.z);
  camera.rotation.set(ptrEase.y * PAR_PITCH, -ptrEase.x * PAR_YAW, 0);
}

/* ============================================================== frame loop */
let running = false, userPaused = false, docHidden = false, reduced = false;
let rafId = 0, lastTs = 0, acc = 0, fpsEma = 60, panelAcc = 0;
let ready = false;

function frame(ts) {
  rafId = requestAnimationFrame(frame);
  let raw = (ts - lastTs) / 1000;
  lastTs = ts;
  if (!(raw > 0)) raw = 0;
  if (raw > L.CFG.MAX_FRAME_DT) raw = L.CFG.MAX_FRAME_DT;

  fpsEma += ((raw > 0.0005 ? 1 / raw : 60) - fpsEma) * 0.08;

  acc += raw;
  let n = 0;
  while (acc >= L.CFG.FIXED_DT && n < L.CFG.MAX_SUBSTEPS) {
    L.step(L.CFG.FIXED_DT); acc -= L.CFG.FIXED_DT; n++;
  }
  if (n === L.CFG.MAX_SUBSTEPS) acc = 0;

  updateCamera(raw || 1 / 60);
  syncLeaves();
  renderer.render(scene, camera);

  panelAcc += raw;
  if (panelAcc > 0.25) { panelAcc = 0; updatePanel(); }
}

function start() {
  if (running || reduced || userPaused || docHidden || !ready) return;
  running = true;
  lastTs = performance.now();
  acc = 0;
  rafId = requestAnimationFrame(frame);
}
function stop() {
  if (!running) return;
  running = false;
  if (rafId) cancelAnimationFrame(rafId);
  rafId = 0;
}
function renderOnce() {
  updateCamera(1);
  syncLeaves();
  renderer.render(scene, camera);
}

/* ------------------------------------------------------------- environment */
const mq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
if (mq) {
  reduced = !!mq.matches;
  const onChange = e => {
    reduced = e.matches;
    if (reduced) { stop(); L.staticFrame(); renderOnce(); } else start();
  };
  if (mq.addEventListener) mq.addEventListener('change', onChange);
}

document.addEventListener('visibilitychange', () => {
  docHidden = !!document.hidden;
  if (docHidden) stop(); else start();
});
window.addEventListener('resize', () => { resize(); if (!running) renderOnce(); });
window.addEventListener('orientationchange', () => { resize(); if (!running) renderOnce(); });

canvas.addEventListener('webglcontextlost', e => {
  e.preventDefault();
  stop();
  fail('The browser dropped this page’s WebGL context. A still frame is shown instead.');
}, false);

/* =============================================================== dev panel */
const elInt = document.getElementById('intensity');
const elVInt = document.getElementById('v-int');
const elFps = document.getElementById('v-fps');
const elCount = document.getElementById('v-count');
const elBytes = document.getElementById('v-bytes');
const elCalls = document.getElementById('v-calls');
const elHeap = document.getElementById('v-heap');

function totalBytes() {
  let sum = 0;
  const nav = performance.getEntriesByType('navigation')[0];
  if (nav) sum += nav.transferSize || nav.encodedBodySize || 0;
  for (const r of performance.getEntriesByType('resource')) {
    sum += r.transferSize || r.encodedBodySize || 0;
  }
  return sum;
}
function fmt(b) {
  return b >= 1048576 ? (b / 1048576).toFixed(2) + ' MB'
       : b >= 1024 ? (b / 1024).toFixed(1) + ' KB' : b + ' B';
}
function updatePanel() {
  if (elFps) elFps.textContent = reduced ? '— (reduced motion)' : fpsEma.toFixed(0);
  if (elCount) elCount.textContent = L.getActiveCount();
  if (elBytes) elBytes.textContent = fmt(totalBytes());
  if (elCalls) elCalls.textContent = renderer.info.render.calls + ' / ' +
      (renderer.info.render.triangles / 1000).toFixed(1) + 'k tri';
  if (elHeap && performance.memory) {
    elHeap.textContent = (performance.memory.usedJSHeapSize / 1048576).toFixed(1) + ' MB';
  } else if (elHeap) { elHeap.textContent = 'n/a'; }
}
function setFromPanel(v) {
  L.setIntensity(v);
  if (elInt) elInt.value = v;
  if (elVInt) elVInt.textContent = (+v).toFixed(2);
}
if (elInt) elInt.addEventListener('input', () => setFromPanel(elInt.value));
const bind = (id, fn) => { const e = document.getElementById(id); if (e) e.addEventListener('click', fn); };
bind('b-0', () => setFromPanel(0));
bind('b-35', () => setFromPanel(0.35));
bind('b-1', () => setFromPanel(1));
bind('b-12', () => setFromPanel(1.2));
bind('b-pause', function () {
  if (running) { window.heroDemo.pause(); this.textContent = 'resume'; }
  else { window.heroDemo.resume(); this.textContent = 'pause'; }
});

/* ============================================================== public API */
window.heroDemo = {
  setIntensity(v) { L.setIntensity(v); if (!running) renderOnce(); },
  getIntensity() { return L.getIntensity(); },
  pause() { userPaused = true; stop(); },
  resume() { userPaused = false; start(); },
  count() { return L.getActiveCount(); },
  bytes: totalBytes,
  _internals: {
    THREE_camera: camera, scene, renderer, layout: LAYOUT, leaves: L,
    isRunning: () => running,
    info: () => ({ calls: renderer.info.render.calls,
                   tris: renderer.info.render.triangles,
                   programs: renderer.info.programs.length,
                   textures: renderer.info.memory.textures,
                   geometries: renderer.info.memory.geometries }),
    parts,
    /* live layout tuning: the numbers in LAYOUT were found with this, driven
       from tools/tune.mjs, not guessed. */
    applyLayout(patch) {
      if (patch) for (const k in patch) Object.assign(LAYOUT[k] ?? (LAYOUT[k] = {}), patch[k]);
      if (parts.fuji) place(parts.fuji, LAYOUT.fuji);
      if (parts.pagoda) place(parts.pagoda, LAYOUT.pagoda);
      if (parts.tree) place(parts.tree, LAYOUT.tree);
      if (parts.portrait) {
        parts.portrait.position.set(LAYOUT.portrait.x, LAYOUT.portrait.y, LAYOUT.portrait.z);
        parts.portrait.geometry.dispose();
        parts.portrait.geometry = new PlaneGeometry(LAYOUT.portrait.h * 0.8, LAYOUT.portrait.h);
      }
      camera.fov = LAYOUT.fov; camera.updateProjectionMatrix();
      projTan = Math.tan(MathUtils.degToRad(camera.fov) * 0.5);
      if (!running) renderOnce();
      return LAYOUT;
    },
    show(name, v) { if (parts[name]) parts[name].visible = v; if (!running) renderOnce(); },
    screenBox(name) {
      const o = parts[name]; if (!o) return null;
      o.updateWorldMatrix(true, true);
      const box = new Box3().setFromObject(o);
      if (!isFinite(box.min.x)) return null;
      const pts = [], v = new Vector3();
      for (let i = 0; i < 8; i++) {
        v.set(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z);
        v.project(camera);
        pts.push([(v.x * 0.5 + 0.5), (-v.y * 0.5 + 0.5)]);
      }
      return { x0: Math.min(...pts.map(p => p[0])), x1: Math.max(...pts.map(p => p[0])),
               y0: Math.min(...pts.map(p => p[1])), y1: Math.max(...pts.map(p => p[1])) };
    },
    /* Times the WHOLE per-frame cost: one physics substep, the instance
       rebuild, the draw submission, and a glFinish so the GPU is actually
       done. Not a rAF interval -- rAF intervals measure the compositor. */
    bench(n) {
      const gl2 = renderer.getContext();
      for (let i = 0; i < 30; i++) { L.step(L.CFG.FIXED_DT); syncLeaves(); renderer.render(scene, camera); }
      gl2.finish();
      const t0 = performance.now();
      for (let i = 0; i < n; i++) { L.step(L.CFG.FIXED_DT); syncLeaves(); }
      const t1 = performance.now();
      for (let i = 0; i < n; i++) renderer.render(scene, camera);
      gl2.finish();
      const t2 = performance.now();
      return { sim: (t1 - t0) / n, draw: (t2 - t1) / n, total: (t2 - t0) / n,
               px: renderer.domElement.width * renderer.domElement.height };
    },
    setPointer(x, y) { ptr.set(x, y); },
    snapPointer(x, y) { ptr.set(x, y); ptrEase.set(x, y); if (!running) renderOnce(); }
  }
};

/* ==================================================================== boot */
resize();
docHidden = !!document.hidden;
setFromPanel(0.55);

READY.then(() => {
  ready = true;
  restage();
  resize();
  document.body.classList.add('loaded');
  if (reduced) { L.staticFrame(); renderOnce(); }
  else {
    // let the physics settle so the frame does not open on an empty sky
    for (let i = 0; i < 9 * 120; i++) L.step(L.CFG.FIXED_DT);
    start();
  }
  updatePanel();
}).catch(err => {
  console.error(err);
  fail('The scene assets failed to load: ' + err.message);
});
