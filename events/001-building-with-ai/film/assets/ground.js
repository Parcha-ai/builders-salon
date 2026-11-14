/* The speakers' ground: a faint survey grid on ink. Its nodes gather into drifting clusters of
   isometric jacks (the three axes the slabs are drawn on), joined by faint struts where
   neighbours are lit. Clusters favour the top and bottom of the frame so faces and type stay clean. */
(function () {
  const { lerp, hash, PAPER, RED, REEL, W, H } = BS;
  const GS = 40; // grid pitch, px
  const COLS = Math.ceil(W / GS), ROWS = Math.ceil(H / GS);
  const THRESHOLD = 0.5; // noise level where a node becomes a jack
  const AXES = [Math.PI / 2, Math.PI / 6, (5 * Math.PI) / 6].map((a) => [Math.cos(a), Math.sin(a)]);

  /** smooth value noise on the integer lattice */
  function valueNoise(x, y) {
    const ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
    const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
    const h = (i, j) => hash(i * 1013 + j * 7919 + 100000, 77);
    return lerp(lerp(h(ix, iy), h(ix + 1, iy), sx), lerp(h(ix, iy + 1), h(ix + 1, iy + 1), sx), sy);
  }

  /** 0 = plain dot, (0, 1] = jack strength, for every node at time t */
  function litNodes(t) {
    const lit = new Float32Array(COLS * ROWS);
    for (let r = 0; r < ROWS; r++)
      for (let c = 0; c < COLS; c++) {
        const x = c * GS + GS / 2, y = r * GS + GS / 2;
        const nx = (x + t * 16) / 300, ny = (y - t * 7) / 300; // the field drifts right and up
        const n = 0.62 * valueNoise(nx, ny) + 0.38 * valueNoise(nx * 2.3 + 5.1, ny * 2.3 + 9.7);
        const edge = Math.min(1, Math.max(0, Math.max(Math.abs(x / W - 0.5) * (REEL ? 0.8 : 0.72), Math.abs(y / H - 0.5)) * 2 * 1.25 - 0.3));
        const v = n * (0.45 + 0.75 * edge);
        lit[r * COLS + c] = v > THRESHOLD ? Math.min(1, ((v - THRESHOLD) / (1 - THRESHOLD)) * 2.2) : 0;
      }
    return lit;
  }

  function drawGround(ctx, t, fade = 1) {
    if (fade <= 0) return;
    const lit = litNodes(t);
    const at = (r, c) => [c * GS + GS / 2, r * GS + GS / 2];

    ctx.fillStyle = PAPER;
    ctx.globalAlpha = 0.07 * fade;
    for (let r = 0; r < ROWS; r++)
      for (let c = 0; c < COLS; c++) {
        if (lit[r * COLS + c]) continue;
        const [x, y] = at(r, c);
        ctx.fillRect(x - 1, y - 1, 2, 2);
      }

    ctx.strokeStyle = RED;
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let r = 0; r < ROWS; r++)
      for (let c = 0; c < COLS; c++) {
        if (!lit[r * COLS + c]) continue;
        const [x, y] = at(r, c);
        if (c + 1 < COLS && lit[r * COLS + c + 1]) { ctx.moveTo(x, y); ctx.lineTo(x + GS, y); }
        if (r + 1 < ROWS && lit[(r + 1) * COLS + c]) { ctx.moveTo(x, y); ctx.lineTo(x, y + GS); }
      }
    ctx.stroke();

    for (let r = 0; r < ROWS; r++)
      for (let c = 0; c < COLS; c++) {
        const q = lit[r * COLS + c];
        if (!q) continue;
        const [x, y] = at(r, c);
        const twinkle = 0.72 + 0.28 * Math.sin(t * 2.4 + hash(r * COLS + c, 41) * 6.283);
        const size = 4 + 9 * q;
        ctx.globalAlpha = (0.1 + 0.26 * q) * twinkle * fade;
        ctx.lineWidth = 1.4 + 1.2 * q;
        ctx.beginPath();
        for (const [dx, dy] of AXES) { ctx.moveTo(x - dx * size, y - dy * size); ctx.lineTo(x + dx * size, y + dy * size); }
        ctx.stroke();
      }
    ctx.globalAlpha = 1;
  }

  BS.drawGround = drawGround;
})();
