/* Glyph field: every particle is one character of generate.py.
   Shapes are point sets (code ground, logo masks, the B face, headshot luminance grids);
   the field morphs particle i from its point in one shape to its point in the next.
   Everything is a pure function of (shapes, progress, time): any frame renders on its own. */
(function () {
  const { lerp, clamp, ease, seg, codePos, bPlace, D, G, PAPER, INK, RED, REEL, W, H, CODE } = BS;
  const FD = window.BS_FIELD;

  /* ---------------- shared placements (scenes hand shapes to each other) ---------------- */
  const PL = REEL
    ? {
        HERO: { x: 330, y: 800, H: 480 }, ARCH: { x: 150, y: 900, s: 0.82 },
        END_B: { x: 339, y: 596, H: 640 },
      }
    : {
        HERO: { x: 1160, y: 160, H: 760 }, ARCH: { x: 1000, y: 640, s: 0.95 },
        END_B: { x: 760, y: 176, H: 640 },
      };

  /* ---------------- deterministic noise ---------------- */
  function hash(i, j = 0) {
    let x = Math.imul(i | 0, 374761393) ^ Math.imul(j | 0, 668265263) ^ 0x5bd1e995;
    x = Math.imul(x ^ (x >>> 13), 1274126177);
    return ((x ^ (x >>> 16)) >>> 0) / 4294967296;
  }
  // glyph pool: the non-space characters of the source, in order
  const POOL = D.code.join("").replace(/\s+/g, "").replace(/[“”‘’]/g, "'");
  const poolChar = (i, j = 0) => POOL[Math.floor(hash(i, j) * POOL.length)];
  // luminance ramp for portraits, sparse to dense
  const RAMP = " .:-=+*%#@";

  const hex = (c) => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
  const C = { paper: hex(PAPER), ink: hex(INK), red: hex(RED), faint: hex("#D6D2C9") };

  /* ---------------- shapes: { pts: [{x,y,c:[r,g,b],a,s,g}] } ---------------- */
  /** the actual characters of the code ground, where the code layer draws them */
  function codeShape() {
    const pts = [];
    const max = Math.min(D.code.length, CODE.rowsPerCol * CODE.cols);
    for (let r = 0; r < max; r++) {
      const line = D.code[r];
      for (let c = 0; c < line.length; c++) {
        const ch = line[c];
        if (ch === " ") continue;
        const [x, y] = codePos(r, c + 0.5);
        pts.push({ x, y: y + CODE.font * 0.36, c: C.faint, a: 1, s: CODE.font, g: ch });
      }
    }
    return { pts };
  }
  // dense glyphs (from the same source) read as solid ink at small sizes
  const DENSE = POOL.split("").filter((c) => "ABDEGHKMNOPQRSUWXZbdgmpqw#%@&$0689".includes(c)).join("");
  /** official logo coverage mask, one dense glyph per covered cell, tagged for the tile resolve.
      box {x,y,w}: where the full image element is drawn */
  function logoShape(name, box, color, gl = 1.75) {
    const L = FD.logos[name];
    const cell = box.w / L.cols;
    const pts = [];
    for (let r = 0; r < L.rows; r++)
      for (let c = 0; c < L.cols; c++) {
        const k = r * L.cols + c;
        if (L.m[k] === "1")
          pts.push({ x: box.x + (c + 0.5) * cell, y: box.y + (r + 0.5) * cell + cell * 0.6, c: color, a: 1, s: cell * gl, g: DENSE[(c * 7919 + r * 104729) % DENSE.length], cell: k, who: name });
      }
    return { pts, cell };
  }
  /** the B front face (OUTER minus the counters) sampled on a grid; place {x,y,H} */
  function inside(poly, x, y) {
    let o = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const [xi, yi] = poly[i], [xj, yj] = poly[j];
      if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) o = !o;
    }
    return o;
  }
  function bShape(place, cell, color, gl = 1.3) {
    const b = bPlace(place);
    const pts = [];
    const x0 = place.x, y0 = place.y - G.DY * b.k;
    for (let y = y0 + cell / 2; y < y0 + 200 * b.k; y += cell)
      for (let x = x0 + cell / 2; x < x0 + 146 * b.k; x += cell) {
        const u = (x - x0) / b.k, v = (y - y0) / b.k;
        if (inside(G.OUTER, u, v) && !inside(G.UPPER, u, v) && !inside(G.LOWER, u, v))
          pts.push({ x, y: y + cell * 0.4, c: color, a: 1, s: cell * gl, g: null });
      }
    return { pts };
  }
  /** a headshot as a code-glyph halftone on a paper card: darker cells draw bigger ink glyphs,
      contour cells draw vermilion. Each point keeps its cell index for the photo resolve. */
  function portraitShape(id, box, who = 0) {
    const P = FD.portraits[id];
    const cw = box.w / P.cols, ch = box.h / P.rows, cell = Math.min(cw, ch);
    const pts = [];
    for (let r = 0; r < P.rows; r++)
      for (let c = 0; c < P.cols; c++) {
        const k = r * P.cols + c;
        const v = +P.v[k] / 9, red = P.e[k] === "1";
        const s = red ? cell * 1.35 : cell * 1.6 * Math.pow(v, 0.9);
        if (s < 3.4) continue;
        pts.push({ x: box.x + (c + 0.5) * cw, y: box.y + (r + 0.5) * ch + s * 0.36, c: red ? C.red : C.ink, a: 1, s, g: POOL[(c * 7919 + r * 104729) % POOL.length], cell: k, who });
      }
    return { pts };
  }
  const merge = (...shapes) => ({ pts: shapes.flatMap((s) => s.pts) });

  /* ---------------- the field ---------------- */
  // Z-order key keeps neighbourhoods together, so a region of one shape flows to the matching region of the next
  function morton(x, y) {
    let X = clamp(Math.round((x / W) * 1023), 0, 1023), Y = clamp(Math.round((y / H) * 1023), 0, 1023), k = 0;
    for (let b = 9; b >= 0; b--) k = k * 4 + ((Y >> b) & 1) * 2 + ((X >> b) & 1);
    return k;
  }
  /** maps N particles proportionally onto a shape's points (sorted); extra particles share a point invisibly */
  function assign(shape, N) {
    const pts = shape.pts.slice().sort((p, q) => morton(p.x, p.y) - morton(q.x, q.y));
    const n = pts.length;
    const out = new Array(N);
    let last = -1;
    for (let i = 0; i < N; i++) {
      const j = Math.min(n - 1, Math.floor((i * n) / N));
      const p = pts[j];
      out[i] = { x: p.x, y: p.y, c: p.c, a: j === last ? 0 : p.a, s: p.s, g: p.g, cell: p.cell, who: p.who };
      last = j;
    }
    return out;
  }

  function Field(N, seed = 1) {
    this.N = N;
    this.seed = seed;
    this.font = "";
  }
  Field.prototype.shape = function (shape) {
    return assign(shape, this.N);
  };
  /**
   * draws the morph A -> B at progress p (0..1).
   * opts: { t (for flicker), spread (stagger share), arc, alpha, shimmer, lift }
   */
  Field.prototype.draw = function (ctx, A, B, p, opts = {}) {
    const N = this.N, t = opts.t || 0, spread = opts.spread === undefined ? 0.45 : opts.spread;
    const arc = opts.arc === undefined ? 0.22 : opts.arc;
    const alpha = opts.alpha === undefined ? 1 : opts.alpha;
    if (alpha <= 0.002) return;
    const shimmer = opts.shimmer || 0;
    const eq = ease(opts.ease || "power3.inOut");
    const tick = Math.floor(t * 24);
    ctx.save();
    ctx.textAlign = "center";
    ctx.textBaseline = "alphabetic";
    let curFont = -1, curFill = "";
    for (let i = 0; i < N; i++) {
      const a = A[i], b = B[i];
      const d = hash(i, this.seed) * spread;
      const l = p <= 0 ? 0 : p >= 1 ? 1 : clamp((p - d) / (1 - spread));
      const e = eq(l);
      let al = lerp(a.a, b.a, e) * alpha;
      // a resting glyph can be faded / shrunk by the scene (the photo resolve)
      let sm = 1;
      if (opts.mod && (l <= 0 || l >= 1)) {
        const m = opts.mod(l <= 0 ? a : b);
        al *= m[0];
        sm = m[1];
      }
      if (al < 0.02) continue;
      let x = lerp(a.x, b.x, e), y = lerp(a.y, b.y, e);
      const mid = Math.sin(Math.PI * l);
      if (mid > 0.001) {
        const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1;
        const o = mid * len * arc * (hash(i, this.seed + 9) * 2 - 1);
        x += (-dy / len) * o;
        y += (dx / len) * o;
      }
      const s = lerp(a.s, b.s, e) * (1 + (opts.lift || 0.5) * mid) * sm;
      const fs = Math.max(4, Math.round(s));
      if (fs !== curFont) {
        ctx.font = `${opts.weight || 500} ${fs}px "BS Mono", monospace`;
        curFont = fs;
      }
      // in flight the glyph decodes through random characters; at rest it shows its own
      let g;
      const rest = l <= 0 ? a : l >= 1 ? b : null;
      if (!rest || (shimmer && hash(i, tick + 31) < shimmer)) g = poolChar(i, tick);
      else g = rest.g || poolChar(i, 5);
      const ca = a.c, cb = b.c;
      // flying glyphs flash vermilion
      const hot = mid * 0.85;
      const r = lerp(lerp(ca[0], cb[0], e), C.red[0], hot), gg = lerp(lerp(ca[1], cb[1], e), C.red[1], hot), bb = lerp(lerp(ca[2], cb[2], e), C.red[2], hot);
      const fill = `rgba(${r | 0},${gg | 0},${bb | 0},${al.toFixed(3)})`;
      if (fill !== curFill) {
        ctx.fillStyle = fill;
        curFill = fill;
      }
      ctx.fillText(g, x, y);
    }
    ctx.restore();
  };

  /* ---------------- decode text ---------------- */
  /**
   * splits an element into letter spans and drives a decode in / decode out from time t.
   * win: { in, out, stagger, dur, hot (scramble colour) }
   */
  function Decoder(el, opts = {}) {
    this.letters = [];
    const walk = (node) => {
      for (const child of Array.from(node.childNodes)) {
        if (child.nodeType === 3) {
          // letters live inside per-word nowrap spans, so lines only break between words
          const frag = document.createDocumentFragment();
          let word = null;
          for (const ch of child.textContent) {
            if (ch === "\n" || ch === " ") {
              word = null;
              frag.appendChild(ch === "\n" ? document.createElement("br") : document.createTextNode(" "));
              continue;
            }
            if (!word) {
              word = document.createElement("span");
              word.style.whiteSpace = "nowrap";
              frag.appendChild(word);
            }
            const s = document.createElement("span");
            s.textContent = ch;
            s.style.display = "inline-block";
            word.appendChild(s);
            this.letters.push({ el: s, ch });
          }
          node.replaceChild(frag, child);
        } else if (child.nodeType === 1 && child.tagName !== "BR") walk(child);
      }
    };
    walk(el);
    this.seed = opts.seed || 3;
    this.hot = opts.hot || RED;
  }
  Decoder.prototype.frame = function (t, w) {
    const stagger = w.stagger === undefined ? 0.012 : w.stagger, dur = w.dur === undefined ? 0.16 : w.dur;
    const outStagger = w.outStagger === undefined ? stagger * 0.5 : w.outStagger;
    const tick = Math.floor(t * 30);
    this.letters.forEach((L, i) => {
      const tin = w.in + i * stagger;
      const tout = w.out === undefined ? Infinity : w.out + i * outStagger;
      let state;
      if (t < tin - (w.pre || 0)) state = 0;
      else if (t < tin + dur) state = 1;
      else if (t < tout) state = 2;
      else if (t < tout + dur * 0.8) state = 1;
      else state = 0;
      if (state === 0) { L.el.style.opacity = 0; return; }
      L.el.style.opacity = 1;
      if (state === 1) {
        L.el.textContent = poolChar(i + this.seed * 1000, tick);
        L.el.style.color = this.hot;
      } else {
        L.el.textContent = L.ch;
        L.el.style.color = "";
      }
    });
  };

  /* ---------------- the B peeled layer by layer (10 s and 24.7 s transitions) ---------------- */
  // the B's 14 outline layers (front + 13 extrusion steps), each peeling toward the camera on its
  // own start time: a small dip back (back.in), a slide to the front, then a rush past with a twist
  const PEEL_STARTS = [0, 0.07, 0.12, 0.18, 0.22, 0.26, 0.29, 0.32, 0.35, 0.38, 0.4, 0.42, 0.44, 0.46];
  const PEEL_ANCHOR = [16, 104]; // mid-stem, B units
  function peelAnchor(place) { return bPlace(place).f(PEEL_ANCHOR); }
  /** opts: { T0, k (time scale on PEEL_STARTS), dur(i), alpha, grow (extrusion 0..1 before the peel), color } */
  function drawPeel(ctx, place, t, opts) {
    const bp = bPlace(place), A0 = bp.f(PEEL_ANCHOR);
    const SMAX = (6 * Math.max(W, H)) / (16 * bp.k);
    const k = opts.k || 1, grow = opts.grow === undefined ? 1 : opts.grow;
    const backIn = (u, o = 1.9) => u * u * ((o + 1) * u - o);
    ctx.save();
    ctx.strokeStyle = opts.color || RED;
    ctx.lineCap = "square";
    ctx.lineJoin = "miter";
    const A = opts.alpha === undefined ? 1 : opts.alpha;
    for (let i = 13; i >= 0; i--) {
      const st = opts.T0 + PEEL_STARTS[i] * k, dur = opts.dur ? opts.dur(i) : 0.27 - 0.005 * i;
      const u = clamp((t - st) / dur);
      if (u >= 1) continue;
      const ez = backIn(u);
      const S = Math.exp(Math.log(SMAX) * ez);
      const slide = 1 - ease("power2.out")(clamp(u * 2.5));
      const off = [bp.E[0] * (i / 13) * slide * grow, bp.E[1] * (i / 13) * slide * grow];
      const rot = (((i * 7919) % 13) / 13 - 0.5) * 0.22 * Math.max(0, ez);
      const cr = Math.cos(rot), sr = Math.sin(rot), kk = bp.k * S;
      const f = (p) => {
        const x = (p[0] - PEEL_ANCHOR[0]) * kk, y = (p[1] - PEEL_ANCHOR[1]) * kk;
        return [A0[0] + off[0] + x * cr - y * sr, A0[1] + off[1] + x * sr + y * cr];
      };
      const base = i === 0 ? bp.front : bp.side;
      ctx.lineWidth = Math.min(base * (1 + 1.4 * Math.log(Math.max(1, S))), 26);
      ctx.globalAlpha = A * (1 - seg(Math.log(S) / Math.log(SMAX), 0.7, 1));
      for (const poly of [G.OUTER, G.UPPER, G.LOWER]) {
        const pts = poly.map(f);
        ctx.beginPath();
        ctx.moveTo(pts[0][0], pts[0][1]);
        for (let j = 1; j < pts.length; j++) ctx.lineTo(pts[j][0], pts[j][1]);
        ctx.closePath();
        ctx.stroke();
      }
    }
    ctx.restore();
  }
  /** square tiles laid in from a point outward: the next scene's ground arriving */
  function drawTileFlood(ctx, A0, t, t0, span, color, TS = 48) {
    if (t <= t0) return;
    const cols = Math.ceil(W / TS), rows = Math.ceil(H / TS);
    let mx = 0;
    for (const [cx, cy] of [[0, 0], [W, 0], [0, H], [W, H]]) mx = Math.max(mx, Math.hypot(cx - A0[0], cy - A0[1]));
    ctx.fillStyle = color;
    for (let r = 0; r < rows; r++)
      for (let c = 0; c < cols; c++) {
        const x = c * TS, y = r * TS;
        const d = Math.hypot(x + TS / 2 - A0[0], y + TS / 2 - A0[1]) / mx;
        const st = t0 + Math.pow(d, 0.8) * span + (((r * 31 + c * 17) % 7) / 7) * 0.03;
        const q = ease("power2.out")(clamp((t - st) / 0.08));
        if (q <= 0) continue;
        const w = TS * q + 0.6;
        ctx.fillRect(x + (TS - w) / 2, y + (TS - w) / 2, w, w);
      }
  }

  Object.assign(BS, { FD, PL, COL: C, hash, poolChar, Field, codeShape, logoShape, bShape, portraitShape, merge, Decoder, drawPeel, drawTileFlood, peelAnchor });
})();
