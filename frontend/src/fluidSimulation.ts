// Lightweight GPU fluid-ink backdrop for the Pagetrail landing page.
// Uses a procedural, domain-warped shader rather than a 3D model or external runtime.
export function fluidSimulation(canvas: HTMLCanvasElement): () => void {
  const gl = canvas.getContext("webgl", {
    alpha: false,
    antialias: false,
    depth: false,
    stencil: false,
    powerPreference: "low-power",
    preserveDrawingBuffer: false,
  });

  if (!gl) {
    canvas.classList.add("webgl-fallback");
    return () => undefined;
  }

  const vertexSource = [
    "attribute vec2 a_position;",
    "varying vec2 v_uv;",
    "void main() {",
    "  v_uv = a_position * 0.5 + 0.5;",
    "  gl_Position = vec4(a_position, 0.0, 1.0);",
    "}",
  ].join("\n");

  const fragmentSource = [
    "precision highp float;",
    "varying vec2 v_uv;",
    "uniform vec2 u_resolution;",
    "uniform float u_time;",
    "uniform vec2 u_mouse;",
    "uniform float u_mouse_strength;",
    "float hash(vec2 p) {",
    "  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);",
    "}",
    "float noise(vec2 p) {",
    "  vec2 i = floor(p);",
    "  vec2 f = fract(p);",
    "  f = f * f * (3.0 - 2.0 * f);",
    "  float a = hash(i);",
    "  float b = hash(i + vec2(1.0, 0.0));",
    "  float c = hash(i + vec2(0.0, 1.0));",
    "  float d = hash(i + vec2(1.0, 1.0));",
    "  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);",
    "}",
    "float fbm(vec2 p) {",
    "  float value = 0.0;",
    "  float amplitude = 0.5;",
    "  mat2 transform = mat2(1.6, 1.2, -1.2, 1.6);",
    "  for (int i = 0; i < 5; i++) {",
    "    value += amplitude * noise(p);",
    "    p = transform * p * 1.18;",
    "    amplitude *= 0.5;",
    "  }",
    "  return value;",
    "}",
    "vec3 inkPalette(float t) {",
    "  vec3 cyan = vec3(0.02, 0.83, 0.82);",
    "  vec3 blue = vec3(0.08, 0.34, 1.00);",
    "  vec3 violet = vec3(0.43, 0.19, 0.96);",
    "  vec3 magenta = vec3(0.94, 0.12, 0.62);",
    "  vec3 first = mix(cyan, blue, smoothstep(0.0, 0.38, t));",
    "  vec3 second = mix(violet, magenta, smoothstep(0.54, 1.0, t));",
    "  return mix(first, second, smoothstep(0.34, 0.78, t));",
    "}",
    "void main() {",
    "  vec2 uv = gl_FragCoord.xy / u_resolution.xy;",
    "  float aspect = u_resolution.x / max(u_resolution.y, 1.0);",
    "  vec2 p = (uv - 0.5) * vec2(aspect, 1.0);",
    "  float t = u_time;",
    "  float orbitAngle = t * 1.56;",
    "  float orbitRadius = 0.31 * (0.72 + 0.28 * sin(orbitAngle * 0.37));",
    "  vec2 autoPoint = vec2(cos(orbitAngle), sin(orbitAngle)) * orbitRadius;",
    "  vec2 autoDelta = (p - autoPoint) * vec2(1.0, 1.0);",
    "  float autoInk = exp(-dot(autoDelta, autoDelta) * 15.0);",
    "  vec2 mousePoint = (u_mouse - 0.5) * vec2(aspect, 1.0);",
    "  float mouseInk = exp(-dot(p - mousePoint, p - mousePoint) * 17.0) * u_mouse_strength;",
    "  float slowA = fbm(p * 1.75 + vec2(t * 0.11, -t * 0.075));",
    "  float slowB = fbm(p * 2.1 + vec2(-t * 0.09, t * 0.12) + vec2(slowA, -slowA) * 1.7);",
    "  vec2 warp = vec2(slowA - 0.5, slowB - 0.5) * 0.95;",
    "  warp += vec2(-autoDelta.y, autoDelta.x) * autoInk * 0.16;",
    "  warp += (p - mousePoint) * mouseInk * -0.14;",
    "  vec2 q = p + warp;",
    "  float flow = fbm(q * 2.65 + vec2(t * 0.07, -t * 0.095));",
    "  float ribbonWave = sin((q.x * 2.3 + q.y * 1.75 + flow * 3.6 + t * 0.16) * 5.0);",
    "  float ribbons = pow(1.0 - abs(ribbonWave), 5.0);",
    "  float fineFlow = fbm(q * 5.4 + vec2(-t * 0.13, t * 0.1));",
    "  float pigment = smoothstep(0.37, 0.78, flow * 0.78 + fineFlow * 0.24 + ribbons * 0.21 + autoInk * 0.25 + mouseInk * 0.3);",
    "  float hue = clamp(flow * 0.62 + fineFlow * 0.18 + ribbons * 0.18 + 0.06 * sin(t * 0.12 + q.y * 3.0), 0.0, 1.0);",
    "  vec3 ink = inkPalette(hue);",
    "  float highlight = ribbons * 0.95 + autoInk * 0.38 + mouseInk * 0.5;",
    "  ink *= 0.5 + highlight;",
    "  float edgeFade = smoothstep(0.92, 0.12, length(p * vec2(0.78, 1.0)));",
    "  vec3 base = vec3(0.004, 0.005, 0.014);",
    "  vec3 color = base + ink * pigment * (0.58 + edgeFade * 0.28);",
    "  color += inkPalette(fract(hue + 0.18)) * ribbons * 0.055;",
    "  float vignette = smoothstep(1.05, 0.18, length(p * vec2(0.62, 0.82)));",
    "  color *= 0.72 + vignette * 0.28;",
    "  gl_FragColor = vec4(color, 1.0);",
    "}",
  ].join("\n");

  function compileShader(type: number, source: string): WebGLShader | null {
    const shader = gl.createShader(type);
    if (!shader) return null;
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      console.warn("Pagetrail fluid shader failed:", gl.getShaderInfoLog(shader));
      gl.deleteShader(shader);
      return null;
    }
    return shader;
  }

  const vertexShader = compileShader(gl.VERTEX_SHADER, vertexSource);
  const fragmentShader = compileShader(gl.FRAGMENT_SHADER, fragmentSource);
  if (!vertexShader || !fragmentShader) {
    canvas.classList.add("webgl-fallback");
    if (vertexShader) gl.deleteShader(vertexShader);
    if (fragmentShader) gl.deleteShader(fragmentShader);
    return () => undefined;
  }

  const program = gl.createProgram();
  if (!program) {
    canvas.classList.add("webgl-fallback");
    gl.deleteShader(vertexShader);
    gl.deleteShader(fragmentShader);
    return () => undefined;
  }

  gl.attachShader(program, vertexShader);
  gl.attachShader(program, fragmentShader);
  gl.linkProgram(program);
  gl.deleteShader(vertexShader);
  gl.deleteShader(fragmentShader);

  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    console.warn("Pagetrail fluid program failed:", gl.getProgramInfoLog(program));
    gl.deleteProgram(program);
    canvas.classList.add("webgl-fallback");
    return () => undefined;
  }

  const buffer = gl.createBuffer();
  if (!buffer) {
    gl.deleteProgram(program);
    canvas.classList.add("webgl-fallback");
    return () => undefined;
  }

  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  gl.useProgram(program);

  const positionLocation = gl.getAttribLocation(program, "a_position");
  const resolutionLocation = gl.getUniformLocation(program, "u_resolution");
  const timeLocation = gl.getUniformLocation(program, "u_time");
  const mouseLocation = gl.getUniformLocation(program, "u_mouse");
  const mouseStrengthLocation = gl.getUniformLocation(program, "u_mouse_strength");

  gl.enableVertexAttribArray(positionLocation);
  gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);
  gl.disable(gl.DEPTH_TEST);
  gl.disable(gl.BLEND);

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const pointer = { x: 0.5, y: 0.5 };
  let mouseStrength = 0;
  let lastPointerAt = 0;
  let startedAt = performance.now();
  let frameId = 0;
  let disposed = false;
  let width = 0;
  let height = 0;
  let pixelRatio = 1;

  function resize() {
    const rect = canvas.getBoundingClientRect();
    pixelRatio = Math.min(window.devicePixelRatio || 1, window.innerWidth < 700 ? 1 : 1.25);
    const nextWidth = Math.max(1, Math.floor(rect.width * pixelRatio));
    const nextHeight = Math.max(1, Math.floor(rect.height * pixelRatio));
    if (nextWidth === width && nextHeight === height) return;
    width = nextWidth;
    height = nextHeight;
    canvas.width = width;
    canvas.height = height;
    gl.viewport(0, 0, width, height);
  }

  function updatePointer(event: PointerEvent) {
    const rect = canvas.getBoundingClientRect();
    pointer.x = Math.min(1, Math.max(0, (event.clientX - rect.left) / Math.max(rect.width, 1)));
    pointer.y = 1 - Math.min(1, Math.max(0, (event.clientY - rect.top) / Math.max(rect.height, 1)));
    lastPointerAt = performance.now();
    mouseStrength = 1;
  }

  function draw(now: number) {
    if (disposed) return;
    resize();
    const elapsed = reducedMotion.matches ? 0.85 : (now - startedAt) / 1000;
    mouseStrength = Math.max(0, 1 - (now - lastPointerAt) / 1400);

    gl.useProgram(program);
    gl.uniform2f(resolutionLocation, width, height);
    gl.uniform1f(timeLocation, elapsed);
    gl.uniform2f(mouseLocation, pointer.x, pointer.y);
    gl.uniform1f(mouseStrengthLocation, mouseStrength);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

    if (!reducedMotion.matches && !document.hidden) {
      frameId = requestAnimationFrame(draw);
    }
  }

  function start() {
    if (disposed || reducedMotion.matches || document.hidden || frameId) return;
    frameId = requestAnimationFrame(draw);
  }

  function onVisibilityChange() {
    if (document.hidden) {
      cancelAnimationFrame(frameId);
      frameId = 0;
      return;
    }
    if (reducedMotion.matches) draw(performance.now());
    else start();
  }

  function onMotionPreferenceChange() {
    cancelAnimationFrame(frameId);
    frameId = 0;
    if (reducedMotion.matches) draw(performance.now());
    else start();
  }

  function onContextLost(event: Event) {
    event.preventDefault();
    cancelAnimationFrame(frameId);
    frameId = 0;
    canvas.classList.add("webgl-fallback");
  }

  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(canvas);
  window.addEventListener("pointermove", updatePointer, { passive: true });
  window.addEventListener("pointerdown", updatePointer, { passive: true });
  document.addEventListener("visibilitychange", onVisibilityChange);
  canvas.addEventListener("webglcontextlost", onContextLost);
  if (typeof reducedMotion.addEventListener === "function") {
    reducedMotion.addEventListener("change", onMotionPreferenceChange);
  } else {
    reducedMotion.addListener(onMotionPreferenceChange);
  }

  resize();
  if (reducedMotion.matches) draw(performance.now());
  else start();

  return () => {
    disposed = true;
    cancelAnimationFrame(frameId);
    resizeObserver.disconnect();
    window.removeEventListener("pointermove", updatePointer);
    window.removeEventListener("pointerdown", updatePointer);
    document.removeEventListener("visibilitychange", onVisibilityChange);
    canvas.removeEventListener("webglcontextlost", onContextLost);
    if (typeof reducedMotion.removeEventListener === "function") {
      reducedMotion.removeEventListener("change", onMotionPreferenceChange);
    } else {
      reducedMotion.removeListener(onMotionPreferenceChange);
    }
    gl.deleteBuffer(buffer);
    gl.deleteProgram(program);
    canvas.classList.remove("webgl-fallback");
  };
}
