/* Builders' Salon geometry engine.
   Every shape is computed from the constants in generate.py (via data.js).
   render functions are pure functions of a state object; scenes derive the state from
   timeline time, so any frame renders identically on its own. */
(function () {
  const D = window.BS_DATA;
  const G = D.geo;
  const PAPER = G.PAPER, INK = G.INK, RED = G.RED;

  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, t) => a + (b - a) * t;
  const lerp2 = (p, q, t) => [lerp(p[0], q[0], t), lerp(p[1], q[1], t)];
  const easeCache = {};
  const ease = (name) => easeCache[name] || (easeCache[name] = name === "none" ? (x) => x : gsap.parseEase(name));
  /** eased 0..1 progress of t through [a, b] */
  const seg = (t, a, b, e = "none") => ease(e)(clamp((t - a) / (b - a)));
  /** keyframes: [[time, value], [time, value, ease-into-this-key], ...] */
  function kf(t, keys) {
    if (t <= keys[0][0]) return keys[0][1];
    for (let i = 1; i < keys.length; i++) {
      const [t1, v1, e] = keys[i];
      if (t <= t1) {
        const [t0, v0] = keys[i - 1];
        return lerp(v0, v1, ease(e || "power2.inOut")((t - t0) / (t1 - t0)));
      }
    }
    return keys[keys.length - 1][1];
  }

  /* ---------------- format ---------------- */
  // each project root sets window.BS_FMT before this file loads: "wide" (1920x1080) or "reel" (1080x1920)
  const REEL = window.BS_FMT === "reel";
  const W = REEL ? 1080 : 1920, H = REEL ? 1920 : 1080;
  /** applies per-format inline styles: { id: {left:"96px", ...} } */
  function lay(map) {
    if (!map) return;
    for (const [id, st] of Object.entries(map)) {
      const el = document.getElementById(id);
      if (el) Object.assign(el.style, st);
    }
  }

  /* ---------------- code ground ---------------- */
  const CODE = REEL
    ? { font: 13, row: 17, colW: 540, top: 8, numX: 14, textX: 52, cw: 7.8, rowsPerCol: 113, cols: 2, numFont: 10 }
    : { font: 15, row: 20, colW: 640, top: 10, numX: 18, textX: 62, cw: 9, rowsPerCol: 54, cols: 3, numFont: 11 };

  /** centre of character `col` (fractional ok) on wrapped source row `row`, in layer px */
  function codePos(row, col) {
    const c = Math.floor(row / CODE.rowsPerCol), r = row % CODE.rowsPerCol;
    return [c * CODE.colW + CODE.textX + col * CODE.cw, CODE.top + r * CODE.row + CODE.row / 2];
  }

  /** builds the code layer; returns handles for rows and highlighted tuples */
  function buildCode(host, { textColor = "#D6D2C9", numColor = "#DEDAD1" } = {}) {
    const marks = {};
    const spanRows = {};
    for (const [name, info] of Object.entries(D.codeSpans)) {
      marks[name] = [];
      for (const s of info.spans) (spanRows[s.row] = spanRows[s.row] || []).push({ ...s, name });
    }
    const rows = [];
    const max = CODE.rowsPerCol * CODE.cols;
    for (let i = 0; i < Math.min(max, D.code.length); i++) {
      const [x, yc] = codePos(i, 0);
      const row = document.createElement("div");
      row.className = "code-row";
      row.style.cssText = `position:absolute;left:${x - CODE.textX + CODE.numX}px;top:${yc - CODE.row / 2}px;height:${CODE.row}px;line-height:${CODE.row}px;white-space:pre;`;
      const num = document.createElement("span");
      num.textContent = String(i + 1).padStart(3, "0");
      num.style.cssText = `display:inline-block;width:${CODE.textX - CODE.numX}px;font-size:${CODE.numFont}px;color:${numColor};vertical-align:top;`;
      row.appendChild(num);
      const text = document.createElement("span");
      text.className = "code-text";
      text.style.cssText = `font-size:${CODE.font}px;color:${textColor};`;
      const line = D.code[i];
      const spans = (spanRows[i] || []).sort((a, b) => a.col - b.col);
      let at = 0;
      for (const s of spans) {
        text.appendChild(document.createTextNode(line.slice(at, s.col)));
        const m = document.createElement("span");
        m.textContent = line.slice(s.col, s.col + s.len);
        text.appendChild(m);
        marks[s.name].push(m);
        at = s.col + s.len;
      }
      text.appendChild(document.createTextNode(line.slice(at)));
      row.appendChild(text);
      host.appendChild(row);
      rows.push({ row, text });
    }
    return { rows, marks };
  }

  /* ---------------- the B and the architecture ---------------- */
  const OUTER = G.OUTER, UPPER = G.UPPER, LOWER = G.LOWER, PROFILE = G.PROFILE;
  // Open path of the B outline, starting bottom-left and climbing the stem, so it
  // lines up vertex for vertex with the stepped architectural profile.
  const B_PATH = [8, 0, 1, 2, 3, 4, 5, 6, 7].map((i) => OUTER[i]);
  const P = PROFILE;
  const A_PATH = [P[0], P[1], P[2], P[3], [(P[3][0] + P[4][0]) / 2, P[3][1]], P[4], P[5], P[6], P[7]];
  const A_MIN = [Math.min(...P.map((p) => p[0])), Math.min(...P.map((p) => p[1])) - 18 * 5];
  const A_SIZE = [Math.max(...P.map((p) => p[0])) + 18 * 16 - A_MIN[0], Math.max(...P.map((p) => p[1])) - A_MIN[1]];
  const N = 19; // slices: the B uses the front + 13 steps, the architecture all 19 layers

  /** B placement {x, y, H} matches bmark(a, x, y, height) in generate.py */
  function bPlace({ x, y, H }) {
    const k = H / (200 - G.DY);
    return {
      k,
      f: (p) => [x + p[0] * k, y + (p[1] - G.DY) * k],
      E: [G.DX * k, G.DY * k],
      side: Math.max(0.55, k * 0.65),
      front: Math.max(1, k * 1.6),
    };
  }
  /** architecture placement {x, y, s}: top-left of its bounding box and scale vs the 1200 flyer */
  function aPlace({ x, y, s }) {
    return {
      f: (p) => [x + (p[0] - A_MIN[0]) * s, y + (p[1] - A_MIN[1]) * s],
      E: [18 * 16 * s, 18 * -5 * s],
    };
  }
  const centroid = (pts) => [pts.reduce((a, p) => a + p[0], 0) / pts.length, pts.reduce((a, p) => a + p[1], 0) / pts.length];

  /**
   * state: { B:{x,y,H}, A:{x,y,s}, m (B->architecture), e (extrusion 0..1), fill (paper fill 0..1),
   *          cam:{yaw,pitch,roll,F,s (1 = approved oblique pose)}, alpha, color, wArch }
   */
  function buildSolid(st) {
    const m = st.m || 0;
    const b = bPlace(st.B);
    const a = aPlace(st.A || { x: 0, y: 0, s: 1 });
    const outer = B_PATH.map((p, j) => lerp2(b.f(p), a.f(A_PATH[j]), m));
    const E = lerp2(b.E, a.E, m);
    const cs = 1 - seg(m, 0, 0.24, "power2.in");
    const counters = [UPPER, LOWER].map((poly) => {
      const pts = poly.map(b.f);
      const c = centroid(pts);
      return pts.map((p) => lerp2(c, p, cs));
    });
    const e = st.e === undefined ? 1 : st.e;
    const ts = [];
    for (let i = 0; i < N; i++) {
      const target = lerp(Math.min(i, 13) / 13, i / 18, m);
      const d = (i / (N - 1)) * 0.55;
      ts.push(target * ease("power3.out")(clamp((e - d) / 0.45)));
    }
    // front-face centre (bounding box of the front outline)
    const xs = outer.map((p) => p[0]), ys = outer.map((p) => p[1]);
    const front = [(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2];
    return {
      m, outer, counters, cs, E, ts, front,
      wSide: lerp(b.side, st.wArch || 2, m),
      wFront: lerp(b.front, st.wArch || 2, m),
      closeA: 1 - seg(m, 0.15, 0.6),
      midA: 1 - seg(m, 0.3, 0.9),
    };
  }

  function makeProjector(solid, cam) {
    const Dz = Math.hypot(solid.E[0], solid.E[1]) || 1;
    const u = [solid.E[0] / Dz, solid.E[1] / Dz];
    const C = [solid.front[0] + solid.E[0] / 2, solid.front[1] + solid.E[1] / 2];
    const yaw = ((cam.yaw || 0) * Math.PI) / 180, pitch = ((cam.pitch || 0) * Math.PI) / 180, roll = ((cam.roll || 0) * Math.PI) / 180;
    const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch), cr = Math.cos(roll), sr = Math.sin(roll);
    const F = cam.F || 2400, s = cam.s === undefined ? 1 : cam.s;
    const off = cam.offset || [0, 0];
    function rot(x, y, z) {
      // yaw (Y), then pitch (X), then roll (Z)
      let x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
      let y1 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
      let x2 = x1 * cr - y1 * sr, y2 = x1 * sr + y1 * cr;
      return [x2, y2, z2];
    }
    function proj(f, t) {
      const wz = t * Dz - Dz / 2;
      // world relative to the solid's centre (front centre pushed half the depth back)
      const X = f[0] - solid.front[0], Y = f[1] - solid.front[1];
      const restX = X + u[0] * wz, restY = Y + u[1] * wz;
      const r = rot(X, Y, wz);
      const k = F / (F + r[2]);
      return [C[0] + lerp(r[0] * k, restX, s) + off[0], C[1] + lerp(r[1] * k, restY, s) + off[1]];
    }
    function depth(t) {
      const wz = t * Dz - Dz / 2;
      return lerp(rot(0, 0, wz)[2], wz, s);
    }
    return { proj, depth };
  }

  function strokePoly(ctx, pts, closed) {
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    if (closed) ctx.closePath();
    ctx.stroke();
  }

  /** draws the extruded B / architecture with painter's-order hidden lines */
  function drawSolid(ctx, st) {
    const solid = buildSolid(st);
    const pr = makeProjector(solid, st.cam || {});
    const color = st.color || RED;
    const fill = st.fill === undefined ? 1 : st.fill;
    const alpha = st.alpha === undefined ? 1 : st.alpha;
    if (alpha <= 0) return;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.lineCap = "square";
    ctx.lineJoin = "miter";
    ctx.miterLimit = 10;
    ctx.strokeStyle = color;
    const flat = solid.ts.every((t) => t < 1e-4);
    const idx = flat ? [0] : solid.ts.map((_, i) => i);
    // farthest first; ties keep the front slice last
    idx.sort((i, j) => pr.depth(solid.ts[j]) - pr.depth(solid.ts[i]) || j - i);
    const contours = (t) => ({
      outer: solid.outer.map((p) => pr.proj(p, t)),
      counters: solid.counters.map((c) => c.map((p) => pr.proj(p, t))),
    });
    const showCounters = solid.cs > 0.02;
    let prev = null;
    for (let n = 0; n < idx.length; n++) {
      const i = idx[n];
      const t = solid.ts[i];
      const c = contours(t);
      // connectors from the previous (farther) slice to this one, along every vertex
      if (prev) {
        ctx.lineWidth = solid.wSide;
        const pc = prev.c;
        for (let v = 0; v < c.outer.length; v++) {
          const a0 = v === 4 ? solid.midA : 1;
          if (a0 <= 0.01) continue;
          ctx.globalAlpha = alpha * a0;
          strokePoly(ctx, [pc.outer[v], c.outer[v]]);
        }
        if (showCounters) {
          ctx.globalAlpha = alpha * Math.min(1, solid.cs * 1.4);
          for (let k = 0; k < 2; k++)
            for (let v = 0; v < c.counters[k].length; v++) strokePoly(ctx, [pc.counters[k][v], c.counters[k][v]]);
        }
        ctx.globalAlpha = alpha;
      }
      if (fill > 0.001) {
        ctx.beginPath();
        ctx.moveTo(c.outer[0][0], c.outer[0][1]);
        for (const p of c.outer.slice(1)) ctx.lineTo(p[0], p[1]);
        ctx.closePath();
        if (showCounters)
          for (const cc of c.counters) {
            ctx.moveTo(cc[0][0], cc[0][1]);
            for (const p of cc.slice(1)) ctx.lineTo(p[0], p[1]);
            ctx.closePath();
          }
        ctx.globalAlpha = alpha * fill;
        ctx.fillStyle = st.fillColor || PAPER;
        ctx.fill("evenodd");
        ctx.globalAlpha = alpha;
      }
      ctx.lineWidth = (i === 0 ? solid.wFront : solid.wSide) + (st.hl !== undefined ? (st.hlw || 3) * Math.max(0, 1 - Math.abs(i - st.hl) / 1.6) : 0);
      strokePoly(ctx, c.outer, false);
      if (solid.closeA > 0.01) {
        ctx.globalAlpha = alpha * solid.closeA;
        strokePoly(ctx, [c.outer[c.outer.length - 1], c.outer[0]]);
        ctx.globalAlpha = alpha;
      }
      if (showCounters) {
        ctx.globalAlpha = alpha * Math.min(1, solid.cs * 1.4);
        for (const cc of c.counters) strokePoly(ctx, cc, true);
        ctx.globalAlpha = alpha;
      }
      prev = { c, t };
    }
    ctx.restore();
    return { solid, pr };
  }

  /* ---------------- photo slabs ---------------- */
  /** extruded block behind a photo. rect {x,y,w,h}; E extrusion px; p {frame, slices} 0..1 */
  function drawSlab(ctx, rect, E, n, p, colors = {}) {
    const { x, y, w, h } = rect;
    const stroke = colors.stroke || RED, fillC = colors.fill || INK;
    ctx.save();
    ctx.lineCap = "square";
    ctx.lineJoin = "miter";
    ctx.strokeStyle = stroke;
    const ts = [];
    for (let i = n; i >= 1; i--) {
      const d = ((i - 1) / n) * 0.5;
      ts.push((i / n) * ease("power3.out")(clamp((p.slices - d) / 0.5)));
    }
    const corners = (t) => [
      [x + E[0] * t, y + E[1] * t],
      [x + w + E[0] * t, y + E[1] * t],
      [x + w + E[0] * t, y + h + E[1] * t],
      [x + E[0] * t, y + h + E[1] * t],
    ];
    if (p.slices > 0) {
      let prev = null;
      for (const t of ts) {
        const c = corners(t);
        if (prev) {
          ctx.lineWidth = colors.side || 1.6;
          for (let v = 0; v < 4; v++) strokePoly(ctx, [prev[v], c[v]]);
        }
        ctx.fillStyle = fillC;
        ctx.beginPath();
        ctx.rect(c[0][0], c[0][1], w, h);
        ctx.fill();
        ctx.lineWidth = colors.side || 1.6;
        strokePoly(ctx, c, true);
        prev = c;
      }
      if (prev) {
        const c0 = corners(0);
        for (let v = 0; v < 4; v++) strokePoly(ctx, [prev[v], c0[v]]);
      }
    }
    if (p.frame > 0) {
      // front frame drawn around the perimeter, outside the photo edge
      const o = (colors.front || 4) / 2;
      const pts = [[x - o, y - o], [x + w + o, y - o], [x + w + o, y + h + o], [x - o, y + h + o], [x - o, y - o]];
      const per = 2 * (w + h + 4 * o);
      let left = per * clamp(p.frame);
      const out = [pts[0]];
      for (let i = 1; i < pts.length && left > 0; i++) {
        const L = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
        if (left >= L) { out.push(pts[i]); left -= L; }
        else { out.push(lerp2(pts[i - 1], pts[i], left / L)); left = 0; }
      }
      ctx.lineWidth = colors.front || 4;
      ctx.fillStyle = fillC;
      if (p.frame >= 1) { ctx.beginPath(); ctx.rect(x, y, w, h); ctx.fill(); }
      strokePoly(ctx, out, false);
    }
    ctx.restore();
  }

  /* ---------------- type ---------------- */
  /** splits an element's text into letters, each a fill copy under a vermilion outline copy */
  function splitConstruct(el, { stroke = RED, width = 2 } = {}) {
    const out = [];
    const walk = (node) => {
      for (const child of Array.from(node.childNodes)) {
        if (child.nodeType === 3) {
          const frag = document.createDocumentFragment();
          for (const ch of child.textContent) {
            if (ch === " ") { frag.appendChild(document.createTextNode(" ")); continue; }
            const L = document.createElement("span");
            L.style.cssText = "position:relative;display:inline-block;";
            const f = document.createElement("span");
            f.textContent = ch;
            f.style.cssText = "display:inline-block;";
            const o = document.createElement("span");
            o.textContent = ch;
            o.style.cssText = `position:absolute;left:0;top:0;color:transparent;-webkit-text-stroke:${width}px ${stroke};`;
            L.appendChild(f);
            L.appendChild(o);
            frag.appendChild(L);
            out.push({ f, o });
          }
          node.replaceChild(frag, child);
        } else if (child.nodeType === 1) walk(child);
      }
    };
    walk(el);
    return out;
  }
  /** outline appears, ink fills it, outline lifts: one letter every `gap` seconds */
  function construct(tl, letters, at, gap = 0.045) {
    letters.forEach((L, i) => {
      const t = at + i * gap;
      tl.fromTo(L.o, { opacity: 0 }, { opacity: 1, duration: 0.05, ease: "none" }, t);
      tl.fromTo(L.f, { opacity: 0 }, { opacity: 1, duration: 0.12, ease: "power2.out" }, t + 0.15);
      tl.to(L.o, { opacity: 0, duration: 0.22, ease: "power1.in" }, t + 0.24);
    });
    return at + letters.length * gap + 0.46;
  }
  /** splits text into plain letter spans */
  function splitLetters(el) {
    const out = [];
    const text = el.textContent;
    el.textContent = "";
    for (const ch of text) {
      const s = document.createElement("span");
      s.textContent = ch;
      s.style.display = "inline-block";
      if (ch === " ") s.style.whiteSpace = "pre";
      el.appendChild(s);
      out.push(s);
    }
    return out;
  }

  function setupCanvas(cv, w = W, h = H, scale = 2) {
    cv.width = w * scale;
    cv.height = h * scale;
    cv.style.width = w + "px";
    cv.style.height = h + "px";
    const ctx = cv.getContext("2d");
    return {
      ctx,
      clear() {
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, cv.width, cv.height);
        ctx.setTransform(scale, 0, 0, scale, 0, 0);
      },
    };
  }

  window.BS = {
    D, G, PAPER, INK, RED, CODE, REEL, W, H, lay, clamp, lerp, ease, seg, kf,
    codePos, buildCode, bPlace, drawSolid, drawSlab, setupCanvas, splitConstruct, construct, splitLetters,
  };
})();
