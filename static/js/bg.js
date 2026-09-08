(function () {
  const canvas = document.createElement("canvas");
  canvas.id = "cyber-bg";
  document.body.prepend(canvas);
  const ctx = canvas.getContext("2d");

  let W, H;
  const NODES = [];
  const BINARY = [];
  const NODE_COUNT = 55;
  const BINARY_COUNT = 18;
  const CONNECT_DIST = 160;

  // ── Resize ──────────────────────────────────────────────
  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  window.addEventListener("resize", resize);
  resize();

  // ── Node (floating dot) ─────────────────────────────────
  function Node() {
    this.x  = Math.random() * W;
    this.y  = Math.random() * H;
    this.vx = (Math.random() - 0.5) * 0.4;
    this.vy = (Math.random() - 0.5) * 0.4;
    this.r  = Math.random() * 2 + 1.2;
    // colour: indigo / cyan / violet
    const palette = ["#6366f1", "#22d3ee", "#a78bfa", "#38bdf8"];
    this.color = palette[Math.floor(Math.random() * palette.length)];
    this.pulse = Math.random() * Math.PI * 2;
  }
  Node.prototype.update = function () {
    this.x += this.vx;
    this.y += this.vy;
    this.pulse += 0.03;
    if (this.x < 0 || this.x > W) this.vx *= -1;
    if (this.y < 0 || this.y > H) this.vy *= -1;
  };
  Node.prototype.draw = function () {
    const glow = Math.sin(this.pulse) * 0.4 + 0.6;
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.r + Math.sin(this.pulse) * 0.8, 0, Math.PI * 2);
    ctx.fillStyle = this.color;
    ctx.globalAlpha = glow * 0.85;
    ctx.fill();
    // outer ring
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.r * 3, 0, Math.PI * 2);
    ctx.strokeStyle = this.color;
    ctx.lineWidth = 0.4;
    ctx.globalAlpha = glow * 0.15;
    ctx.stroke();
    ctx.globalAlpha = 1;
  };

  // ── Binary rain column ──────────────────────────────────
  function BinaryCol() {
    this.reset();
  }
  BinaryCol.prototype.reset = function () {
    this.x     = Math.random() * W;
    this.y     = Math.random() * -H;
    this.speed = Math.random() * 0.6 + 0.3;
    this.chars = Array.from({ length: Math.floor(Math.random() * 12 + 6) },
                   () => Math.random() > 0.5 ? "1" : "0");
    this.alpha = Math.random() * 0.12 + 0.04;
    this.size  = Math.floor(Math.random() * 5 + 9);
  };
  BinaryCol.prototype.update = function () {
    this.y += this.speed;
    if (this.y > H + 200) this.reset();
  };
  BinaryCol.prototype.draw = function () {
    ctx.font = `${this.size}px 'Courier New', monospace`;
    this.chars.forEach((c, i) => {
      const fade = 1 - i / this.chars.length;
      ctx.fillStyle = `rgba(99,102,241,${this.alpha * fade})`;
      ctx.fillText(c, this.x, this.y + i * (this.size + 2));
    });
  };

  // ── Hex grid overlay (static, drawn once) ───────────────
  function drawHexGrid() {
    const size = 48, cols = Math.ceil(W / (size * 1.73)) + 1;
    const rows = Math.ceil(H / (size * 1.5)) + 1;
    ctx.strokeStyle = "rgba(99,102,241,0.04)";
    ctx.lineWidth = 0.8;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const cx = c * size * 1.73 + (r % 2 === 0 ? 0 : size * 0.865);
        const cy = r * size * 1.5;
        hexPath(cx, cy, size);
        ctx.stroke();
      }
    }
  }
  function hexPath(cx, cy, s) {
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const a = Math.PI / 180 * (60 * i - 30);
      i === 0 ? ctx.moveTo(cx + s * Math.cos(a), cy + s * Math.sin(a))
              : ctx.lineTo(cx + s * Math.cos(a), cy + s * Math.sin(a));
    }
    ctx.closePath();
  }

  // ── Init ────────────────────────────────────────────────
  for (let i = 0; i < NODE_COUNT;   i++) NODES.push(new Node());
  for (let i = 0; i < BINARY_COUNT; i++) BINARY.push(new BinaryCol());

  // ── Draw connecting lines between close nodes ───────────
  function drawEdges() {
    for (let i = 0; i < NODES.length; i++) {
      for (let j = i + 1; j < NODES.length; j++) {
        const dx = NODES[i].x - NODES[j].x;
        const dy = NODES[i].y - NODES[j].y;
        const d  = Math.sqrt(dx * dx + dy * dy);
        if (d < CONNECT_DIST) {
          const alpha = (1 - d / CONNECT_DIST) * 0.25;
          ctx.beginPath();
          ctx.moveTo(NODES[i].x, NODES[i].y);
          ctx.lineTo(NODES[j].x, NODES[j].y);
          ctx.strokeStyle = `rgba(99,102,241,${alpha})`;
          ctx.lineWidth = 0.6;
          ctx.stroke();
        }
      }
    }
  }

  // ── Animate ─────────────────────────────────────────────
  function animate() {
    ctx.clearRect(0, 0, W, H);

    drawHexGrid();

    BINARY.forEach(b => { b.update(); b.draw(); });
    drawEdges();
    NODES.forEach(n => { n.update(); n.draw(); });

    requestAnimationFrame(animate);
  }
  animate();
})();
