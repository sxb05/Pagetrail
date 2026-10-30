import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { mergeVertices } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import "./landing.css";

const MODEL_URL =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260929_212926_92423081-b0e4-4f5a-b650-14af6c05c058.glb";

/* ── Vertex shader ─────────────────────────────────────────── */
const vertexShader = /* glsl */ `
  varying vec3 vNormal;
  varying vec3 vEye;

  void main() {
    vec4 worldPos = modelMatrix * vec4(position, 1.0);
    vec4 mvPos    = viewMatrix * worldPos;
    gl_Position   = projectionMatrix * mvPos;
    vNormal = normalize(normalMatrix * normal);
    vEye    = normalize(mvPos.xyz);
  }
`;

/* ── Fragment shader ───────────────────────────────────────── */
const fragmentShader = /* glsl */ `
  uniform sampler2D uTexture;
  uniform vec2  uResolution;
  uniform float uIorR;
  uniform float uIorY;
  uniform float uIorG;
  uniform float uIorC;
  uniform float uIorB;
  uniform float uIorP;
  uniform float uRefractPower;
  uniform float uChromatic;
  uniform float uSaturation;
  uniform float uShininess;
  uniform float uDiffuseness;
  uniform float uFresnelPower;
  uniform vec3  uLight;
  uniform float uBackside;

  varying vec3 vNormal;
  varying vec3 vEye;

  vec3 sat(vec3 col, float s) {
    float luma = dot(col, vec3(0.2125, 0.7154, 0.0721));
    return mix(vec3(luma), col, s);
  }

  float specular(vec3 light, float shininess, float diffuseness) {
    vec3  n       = normalize(vNormal) * (uBackside > 0.5 ? -1.0 : 1.0);
    vec3  eye     = normalize(vEye);
    vec3  lv      = normalize(light);
    vec3  hv      = normalize(-eye + lv);
    float s       = pow(max(dot(n, hv), 0.0), shininess);
    float d       = max(dot(n, lv), 0.0) * diffuseness;
    return s + d;
  }

  void main() {
    vec2  uv  = gl_FragCoord.xy / uResolution;
    vec3  n   = normalize(vNormal);
    if (uBackside > 0.5) n = -n;
    vec3  eye = normalize(vEye);

    vec3 color = vec3(0.0);

    for (int i = 0; i < 16; i++) {
      float slide = float(i) / 16.0 * 0.045;

      vec3 rR = refract(eye, n, 1.0 / uIorR);
      vec3 rY = refract(eye, n, 1.0 / uIorY);
      vec3 rG = refract(eye, n, 1.0 / uIorG);
      vec3 rC = refract(eye, n, 1.0 / uIorC);
      vec3 rB = refract(eye, n, 1.0 / uIorB);
      vec3 rP = refract(eye, n, 1.0 / uIorP);

      float kR = 1.0, kY = 1.0, kG = 2.0, kC = 2.5, kB = 3.0, kP = 1.0;
      float rp = uRefractPower;
      float ch = uChromatic;

      vec4 tR = texture2D(uTexture, uv + rR.xy * (rp + slide * kR) * ch);
      vec4 tY = texture2D(uTexture, uv + rY.xy * (rp + slide * kY) * ch);
      vec4 tG = texture2D(uTexture, uv + rG.xy * (rp + slide * kG) * ch);
      vec4 tC = texture2D(uTexture, uv + rC.xy * (rp + slide * kC) * ch);
      vec4 tB = texture2D(uTexture, uv + rB.xy * (rp + slide * kB) * ch);
      vec4 tP = texture2D(uTexture, uv + rP.xy * (rp + slide * kP) * ch);

      float r = tR.x * 0.5;
      float y = (tY.x * 2.0 + tY.y * 2.0 - tY.z) / 6.0;
      float g = tG.y * 0.5;
      float c = (tC.y * 2.0 + tC.z * 2.0 - tC.x) / 6.0;
      float b = tB.z * 0.5;
      float p = (tP.z * 2.0 + tP.x * 2.0 - tP.y) / 6.0;

      float R = r + (2.0 * p + 2.0 * y - c) / 3.0;
      float G = g + (2.0 * y + 2.0 * c - p) / 3.0;
      float B = b + (2.0 * c + 2.0 * p - y) / 3.0;

      color += vec3(R, G, B);
    }

    color /= 16.0;
    color  = sat(color, uSaturation);

    /* Specular */
    float spec = specular(uLight, uShininess, uDiffuseness)
               + 0.6 * specular(vec3(1.0, 1.0, -1.0), uShininess * 0.6, uDiffuseness * 0.5);
    color += spec * (uBackside > 0.5 ? 0.35 : 1.0);

    /* Fresnel */
    vec3  ni = normalize(vNormal) * (uBackside > 0.5 ? -1.0 : 1.0);
    float f  = pow(1.0 + dot(normalize(vEye), ni), uFresnelPower);
    color    = mix(color, vec3(1.0), f * (uBackside > 0.5 ? 0.25 : 0.55));

    color += vec3(0.004, 0.005, 0.007);
    gl_FragColor = vec4(color, 1.0);
    #include <colorspace_fragment>
  }
`;

/* ── Background quad shaders ───────────────────────────────── */
const bgVertShader = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`;
const bgFragShader = /* glsl */ `
  uniform sampler2D uTex;
  varying vec2 vUv;
  void main() {
    gl_FragColor = texture2D(uTex, vUv);
    #include <colorspace_fragment>
  }
`;

interface Props {
  onEnterApp: () => void;
}

export default function Landing({ onEnterApp }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const loaderRef = useRef<HTMLDivElement>(null);
  const [webglFailed, setWebglFailed] = useState(false);
  const [activeDot, setActiveDot] = useState(1);
  const prefersReducedMotion = useReducedMotion();
  const prefersReducedMotionRef = useRef<boolean | null>(prefersReducedMotion);

  useEffect(() => {
    prefersReducedMotionRef.current = prefersReducedMotion;
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    let disposed = false;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
    } catch (error) {
      console.warn("PageTrail landing: WebGL is unavailable; using the HTML headline fallback.", error);
      setWebglFailed(true);
      loaderRef.current?.classList.add("done");
      return () => {
        disposed = true;
      };
    }

    /* ── Renderer ─────────────────────────────────────────── */
    renderer.setClearColor(0x000000, 1);
    renderer.outputColorSpace = THREE.SRGBColorSpace;

    /* ── Scenes ───────────────────────────────────────────── */
    const scene = new THREE.Scene();
    const bgScene = new THREE.Scene();

    /* ── Camera ───────────────────────────────────────────── */
    const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
    camera.position.set(0, 0, 10);
    camera.lookAt(0, 0, 0);
    const bgCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    /* ── Offscreen headline canvas ────────────────────────── */
    const hCanvas = document.createElement("canvas");
    const context = hCanvas.getContext("2d");
    if (!context) {
      setWebglFailed(true);
      loaderRef.current?.classList.add("done");
      renderer.dispose();
      return () => {
        disposed = true;
      };
    }
    const hCtx = context;
    let headlineTex: THREE.CanvasTexture | null = null;

    function drawHeadline() {
      if (disposed) return;
      const W = canvas!.clientWidth || window.innerWidth;
      const H = canvas!.clientHeight || window.innerHeight;
      const DPR = Math.min(window.devicePixelRatio, 2);
      hCanvas.width = W * DPR;
      hCanvas.height = H * DPR;
      hCtx.setTransform(DPR, 0, 0, DPR, 0, 0);

      hCtx.fillStyle = "#000";
      hCtx.fillRect(0, 0, W, H);

      const mobile = W < 768 || W / H < 1;
      let fs = Math.min(H * 0.21, W * (mobile ? 0.21 : 0.118));

      const lines = ["Your", "documents", "understood."];

      // Scale down to fit widest line
      hCtx.font = `800 ${fs}px Poppins, sans-serif`;
      const maxW = Math.max(...lines.map(l => hCtx.measureText(l).width));
      const maxAllowed = W * (mobile ? 0.9 : 0.5);
      if (maxW > maxAllowed) fs *= maxAllowed / maxW;

      hCtx.font = `800 ${fs}px Poppins, sans-serif`;
      hCtx.fillStyle = "#e9e9e9";
      hCtx.textAlign = "center";
      hCtx.textBaseline = "alphabetic";

      const cx = W * (mobile ? 0.5 : 0.505);
      const cy = H * (mobile ? 0.45 : 0.468);
      const gap = fs * 1.07;
      const cap = fs * 0.7;

      lines.forEach((line, i) => {
        const y = cy + cap / 2 + (i - 1) * gap;
        hCtx.fillText(line, cx, y);
      });

      if (headlineTex) {
        headlineTex.needsUpdate = true;
      } else {
        headlineTex = new THREE.CanvasTexture(hCanvas);
        headlineTex.colorSpace = THREE.SRGBColorSpace;
        headlineTex.minFilter = THREE.LinearFilter;
        headlineTex.generateMipmaps = false;
      }
    }

    /* ── Background quad ──────────────────────────────────── */
    const bgMat = new THREE.ShaderMaterial({
      vertexShader: bgVertShader,
      fragmentShader: bgFragShader,
      uniforms: { uTex: { value: null } },
      depthTest: false,
      depthWrite: false,
    });
    const bgQuad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), bgMat);
    bgQuad.frustumCulled = false;
    bgScene.add(bgQuad);

    /* ── Glass material factory ───────────────────────────── */
    function makeMat(backside: boolean): THREE.ShaderMaterial {
      return new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader,
        side: backside ? THREE.BackSide : THREE.FrontSide,
        uniforms: {
          uTexture: { value: null },
          uResolution: { value: new THREE.Vector2() },
          uIorR: { value: 1.15 },
          uIorY: { value: 1.16 },
          uIorG: { value: 1.18 },
          uIorC: { value: 1.22 },
          uIorB: { value: 1.22 },
          uIorP: { value: 1.22 },
          uRefractPower: { value: backside ? 0.22 : 0.30 },
          uChromatic: { value: 0.5 },
          uSaturation: { value: 1.08 },
          uShininess: { value: 90.0 },
          uDiffuseness: { value: 0.02 },
          uFresnelPower: { value: 5.0 },
          uLight: { value: new THREE.Vector3(-1, 1, 1) },
          uBackside: { value: backside ? 1.0 : 0.0 },
        },
      });
    }

    const frontMat = makeMat(false);
    const backMat = makeMat(true);

    /* ── Render targets ───────────────────────────────────── */
    let rtBack = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType });
    let rtFront = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType });
    backMat.uniforms.uTexture.value = rtBack.texture;
    frontMat.uniforms.uTexture.value = rtFront.texture;

    /* ── Cube scene graph ─────────────────────────────────── */
    const pivot = new THREE.Object3D();
    const spinner = new THREE.Object3D();
    spinner.rotation.set(-0.42, 0.62, 0.18);
    pivot.add(spinner);
    scene.add(pivot);

    let cubeMesh: THREE.Mesh | null = null;

    function buildCubeMesh(inputGeometry: THREE.BufferGeometry): boolean {
      if (disposed || cubeMesh) {
        inputGeometry.dispose();
        return false;
      }

      let geo = inputGeometry;
      try {
        // The glass shader needs positions only. Removing other attributes makes
        // GLB parts compatible before merging and normals are rebuilt below.
        Object.keys(geo.attributes).forEach((name) => {
          if (name !== "position") geo.deleteAttribute(name);
        });

        // Merge consistently non-indexed geometry so mixed GLB index layouts do
        // not make mergeGeometries return null.
        if (geo.index) {
          const nonIndexed = geo.toNonIndexed();
          geo.dispose();
          geo = nonIndexed;
        }

        const welded = mergeVertices(geo, 1e-4);
        if (welded !== geo) geo.dispose();
        geo = welded;
        geo.computeVertexNormals();
        geo.computeBoundingBox();

        const box = geo.boundingBox;
        if (!box || !geo.getAttribute("position")?.count) {
          throw new Error("The glass model has no usable vertex positions.");
        }

        const centre = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        if (!Number.isFinite(maxDim) || maxDim <= 0) {
          throw new Error("The glass model has invalid dimensions.");
        }

        geo.translate(-centre.x, -centre.y, -centre.z);
        geo.scale(1 / maxDim, 1 / maxDim, 1 / maxDim);
        geo.computeVertexNormals();

        const mesh = new THREE.Mesh(geo, frontMat);
        spinner.add(mesh);
        cubeMesh = mesh;
        loaderRef.current?.classList.add("done");
        return true;
      } catch (error) {
        console.warn("PageTrail landing: could not prepare the glass model.", error);
        geo.dispose();
        return false;
      }
    }

    // The source GLB material/texture data is not used by our custom glass shader.
    // Dispose it once its transformed position geometry has been copied.
    function disposeLoadedModel(root: THREE.Object3D) {
      const geometries = new Set<THREE.BufferGeometry>();
      const materials = new Set<THREE.Material>();
      const textures = new Set<THREE.Texture>();
      root.traverse((child) => {
        const mesh = child as THREE.Mesh;
        if (!mesh.isMesh) return;
        geometries.add(mesh.geometry);
        const list = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        list.forEach((material) => {
          materials.add(material);
          Object.values(material).forEach((value) => {
            if (value instanceof THREE.Texture) textures.add(value);
          });
        });
      });
      geometries.forEach((geometry) => geometry.dispose());
      textures.forEach((texture) => texture.dispose());
      materials.forEach((material) => material.dispose());
    }

    // Load GLB, falling back to a rounded box if download or geometry merging fails.
    const loader = new GLTFLoader();
    loader.load(
      MODEL_URL,
      (gltf) => {
        if (disposed) {
          disposeLoadedModel(gltf.scene);
          return;
        }

        const parts: THREE.BufferGeometry[] = [];
        let merged: THREE.BufferGeometry | null = null;
        try {
          gltf.scene.updateMatrixWorld(true);
          gltf.scene.traverse((child) => {
            if (!(child as THREE.Mesh).isMesh) return;
            const mesh = child as THREE.Mesh;
            let geometry = mesh.geometry.clone();
            geometry.applyMatrix4(mesh.matrixWorld);
            Object.keys(geometry.attributes).forEach((name) => {
              if (name !== "position") geometry.deleteAttribute(name);
            });
            if (geometry.index) {
              const nonIndexed = geometry.toNonIndexed();
              geometry.dispose();
              geometry = nonIndexed;
            }
            parts.push(geometry);
          });

          if (parts.length === 1) {
            merged = parts[0];
          } else if (parts.length > 1) {
            merged = mergeGeometries(parts, false);
          }
        } catch (error) {
          console.warn("PageTrail landing: GLB geometry merge failed; using rounded-box fallback.", error);
        }

        parts.forEach((part) => {
          if (part !== merged) part.dispose();
        });

        // Release the loader's source assets; the displayed mesh uses our merged clone.
        disposeLoadedModel(gltf.scene);

        if (!merged || !buildCubeMesh(merged)) fallback();
      },
      undefined,
      () => fallback(),
    );

    function fallback() {
      if (disposed || cubeMesh) return;
      if (!buildCubeMesh(new RoundedBoxGeometry(1, 1, 1, 8, 0.12))) {
        setWebglFailed(true);
        loaderRef.current?.classList.add("done");
      }
    }

    /* ── Layout ───────────────────────────────────────────── */
    function layout() {
      const W = canvas!.clientWidth || window.innerWidth;
      const H = canvas!.clientHeight || window.innerHeight;
      const DPR = Math.min(window.devicePixelRatio, 2);
      const bW = Math.round(W * DPR);
      const bH = Math.round(H * DPR);

      renderer.setPixelRatio(DPR);
      renderer.setSize(W, H, false);

      camera.aspect = W / H;
      camera.updateProjectionMatrix();

      rtBack.dispose();
      rtFront.dispose();
      rtBack = new THREE.WebGLRenderTarget(bW, bH, { type: THREE.HalfFloatType });
      rtFront = new THREE.WebGLRenderTarget(bW, bH, { type: THREE.HalfFloatType });
      backMat.uniforms.uTexture.value = rtBack.texture;
      frontMat.uniforms.uTexture.value = rtFront.texture;

      const res = new THREE.Vector2(bW, bH);
      backMat.uniforms.uResolution.value.copy(res);
      frontMat.uniforms.uResolution.value.copy(res);

      const mobile = W < 768 || W / H < 1;

      // Cube placement
      const fov = THREE.MathUtils.degToRad(30);
      const visH = 2 * Math.tan(fov / 2) * 10;
      const visW = visH * (W / H);
      const sx = mobile ? 0.5 : 0.517;
      const sy = mobile ? 0.45 : 0.488;
      pivot.position.set((sx - 0.5) * visW, (0.5 - sy) * visH, 0);
      const pxEdge = Math.min(H * 0.44, W * (mobile ? 0.45 : 0.29));
      pivot.scale.setScalar((pxEdge / H) * visH);

      drawHeadline();
      if (headlineTex) bgMat.uniforms.uTex.value = headlineTex;
    }

    /* ── Drag / rotation state ────────────────────────────── */
    let dragging = false;
    let lastX = 0, lastY = 0;
    let velX = 0, velY = 0;
    let lastTime = performance.now();

    // Idle drift blend
    let idleBlend = 0; // 0→1 over 1s
    let idleTimer = 0;
    const IDLE_DELAY = 0.6; // seconds before idle drift kicks in
    const IDLE_RAMP = 1.0;

    // Button spin state
    let btnRemaining = 0; // radians left

    function applyQuat(axis: THREE.Vector3, angle: number) {
      const q = new THREE.Quaternion().setFromAxisAngle(axis, angle);
      spinner.quaternion.premultiply(q);
    }

    // Named pointer handlers are removed in cleanup (important with React StrictMode).
    function onPointerDown(e: PointerEvent) {
      if (disposed) return;
      dragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
      velX = velY = 0;
      btnRemaining = 0;
      idleBlend = 0;
      idleTimer = 0;
      canvas!.classList.add("dragging");
      try {
        canvas!.setPointerCapture(e.pointerId);
      } catch {
        // Pointer capture can fail in unusual browser/device states.
      }
    }

    function onPointerMove(e: PointerEvent) {
      if (!dragging || disposed) return;
      const now = performance.now();
      const dt = Math.min((now - lastTime) / 1000, 0.05);
      const dx = (e.clientX - lastX) * 0.008;
      const dy = (e.clientY - lastY) * 0.008;
      lastX = e.clientX;
      lastY = e.clientY;

      if (dt > 0) {
        velX = dx / dt;
        velY = dy / dt;
      }
      lastTime = now;
      applyQuat(new THREE.Vector3(0, 1, 0), dx);
      applyQuat(new THREE.Vector3(1, 0, 0), dy);
    }

    function endDrag() {
      if (!dragging) return;
      dragging = false;
      canvas!.classList.remove("dragging");
      idleTimer = 0;
    }

    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", endDrag);
    canvas.addEventListener("pointercancel", endDrag);
    canvas.addEventListener("lostpointercapture", endDrag);

    function onContextLost(event: Event) {
      event.preventDefault();
      setWebglFailed(true);
      loaderRef.current?.classList.add("done");
    }
    canvas.addEventListener("webglcontextlost", onContextLost);

    /* ── Arrow buttons ────────────────────────────────────── */
    function rotateCube(steps: number) {
      btnRemaining = steps * Math.PI / 2;
      velX = velY = 0;
      idleBlend = 0;
      idleTimer = 0;
    }

    /* ── Animation loop ───────────────────────────────────── */
    let prevNow = performance.now();
    let rafId = 0;

    function tick() {
      if (disposed) return;
      rafId = requestAnimationFrame(tick);
      const now = performance.now();
      const dt = Math.min((now - prevNow) / 1000, 0.05);
      prevNow = now;

      if (!dragging) {
        // Inertia
        velX *= Math.pow(0.94, dt * 60);
        velY *= Math.pow(0.94, dt * 60);
        if (Math.abs(velX) > 0.0001 || Math.abs(velY) > 0.0001) {
          applyQuat(new THREE.Vector3(0, 1, 0), velX * dt);
          applyQuat(new THREE.Vector3(1, 0, 0), velY * dt);
        }

        // Idle drift is disabled for users who request reduced motion.
        if (!prefersReducedMotionRef.current) {
          idleTimer += dt;
          if (idleTimer > IDLE_DELAY) {
            idleBlend = Math.min(idleBlend + dt / IDLE_RAMP, 1);
          }
          if (idleBlend > 0) {
            const drift = 0.0035 * idleBlend;
            const driftX = 0.0012 * idleBlend;
            applyQuat(new THREE.Vector3(0, 1, 0), drift);
            applyQuat(new THREE.Vector3(1, 0, 0), driftX);
          }
        } else {
          idleBlend = 0;
        }

        // Arrow button smooth rotation
        if (Math.abs(btnRemaining) > 0.0005) {
          const step = btnRemaining * Math.min(1, 0.09 * dt * 60);
          btnRemaining -= step;
          applyQuat(new THREE.Vector3(0, 1, 0), step);
        }
      } else {
        idleTimer = 0;
        idleBlend = 0;
      }

      /* ── Two-pass render ──────────────────────────────────── */
      if (cubeMesh && headlineTex) {
        // Pass 1: bg → rtBack
        renderer.setRenderTarget(rtBack);
        renderer.render(bgScene, bgCamera);

        // Pass 2: bg → rtFront, then cube backfaces → rtFront
        renderer.setRenderTarget(rtFront);
        renderer.render(bgScene, bgCamera);
        cubeMesh.material = backMat;
        renderer.autoClear = false;
        renderer.render(scene, camera);
        renderer.autoClear = true;

        // Pass 3: bg → screen, then cube frontfaces → screen
        renderer.setRenderTarget(null);
        renderer.render(bgScene, bgCamera);
        cubeMesh.material = frontMat;
        renderer.autoClear = false;
        renderer.clearDepth();
        renderer.render(scene, camera);
        renderer.autoClear = true;
      } else {
        // Nothing loaded yet; just render background
        renderer.setRenderTarget(null);
        if (headlineTex) renderer.render(bgScene, bgCamera);
      }
    }

    /* ── Font loading + start ─────────────────────────────── */
    let fontTimeoutId = 0;
    const fontTimeout = new Promise<void>((resolve) => {
      fontTimeoutId = window.setTimeout(resolve, 2500);
    });
    const fontProm = Promise.race([
      Promise.all([
        document.fonts.load("800 100px Poppins"),
        document.fonts.ready,
      ]).then(() => undefined),
      fontTimeout,
    ]);

    void fontProm.then(() => {
      window.clearTimeout(fontTimeoutId);
      if (disposed) return;
      layout();
      tick();
    }).catch((error) => {
      console.warn("PageTrail landing: font loading failed; continuing with fallback fonts.", error);
      if (disposed) return;
      layout();
      tick();
    });

    function onFontsLoaded() {
      if (!disposed) drawHeadline();
    }
    document.fonts.addEventListener("loadingdone", onFontsLoaded);

    // Resize observer recalculates canvas, camera, render targets and headline texture.
    const ro = new ResizeObserver(() => {
      if (!disposed) layout();
    });
    ro.observe(canvas);

    const canvasWithControls = canvas as HTMLCanvasElement & { _rotateCube?: (n: number) => void };
    canvasWithControls._rotateCube = rotateCube;

    return () => {
      disposed = true;
      window.clearTimeout(fontTimeoutId);
      cancelAnimationFrame(rafId);
      ro.disconnect();
      document.fonts.removeEventListener("loadingdone", onFontsLoaded);
      canvas.removeEventListener("pointerdown", onPointerDown);
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerup", endDrag);
      canvas.removeEventListener("pointercancel", endDrag);
      canvas.removeEventListener("lostpointercapture", endDrag);
      canvas.removeEventListener("webglcontextlost", onContextLost);
      canvas!.classList.remove("dragging");
      delete canvasWithControls._rotateCube;
      if (cubeMesh) {
        spinner.remove(cubeMesh);
        cubeMesh.geometry.dispose();
      }
      renderer.dispose();
      rtBack.dispose();
      rtFront.dispose();
      headlineTex?.dispose();
      bgQuad.geometry.dispose();
      frontMat.dispose();
      backMat.dispose();
      bgMat.dispose();
    };
  }, []);

  function rotateBy(steps: number) {
    const c = canvasRef.current as (HTMLCanvasElement & { _rotateCube?: (n: number) => void }) | null;
    c?._rotateCube?.(steps);
  }

  function handlePrev() {
    rotateBy(-1);
    setActiveDot((current) => (current + 2) % 3);
  }

  function handleNext() {
    rotateBy(1);
    setActiveDot((current) => (current + 1) % 3);
  }

  function handleDotClick(index: number) {
    const delta = (index - activeDot + 3) % 3;
    rotateBy(delta === 2 ? -1 : delta);
    setActiveDot(index);
  }

  return (
    <div className="landing-root">
      <section className="hero" id="hero">
        {/* Three.js canvas */}
        <canvas id="scene" ref={canvasRef} aria-label="Decorative glass cube. Drag to rotate." />

        {/* Loader overlay */}
        <div className="loader" ref={loaderRef}>
          Loading scene
        </div>

        <div className="ui">
          {/* Accessibility headline */}
          <h1 className={webglFailed ? "hero-fallback-headline" : "sr-only"}>
            Your<br />documents<br />understood.
          </h1>

          {/* ── Navbar ── */}
          <header className="nav">
            <a href="#hero" className="logo" aria-label="PageTrail home">
              <i className="logo-mark" aria-hidden="true" />
              <b>Page</b><span>Trail</span>
            </a>
            <ul className="nav-links">
              <li><button type="button" className="nav-action" onClick={onEnterApp}>Product</button></li>
              <li><a href="#features">Features</a></li>
              <li><a href="#how">How it works</a></li>
            </ul>
          </header>

          {/* ── Arrow buttons ── */}
          <div className="arrows">
            <button className="arrow" id="prev" onClick={handlePrev} aria-label="Previous">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round">
                <path d="M19 12H5M11 6l-6 6 6 6" />
              </svg>
            </button>
            <button className="arrow" id="next" onClick={handleNext} aria-label="Next">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </button>
          </div>

          {/* ── Pagination dots ── */}
          <nav className="dots" aria-label="Glass cube positions">
            {[0, 1, 2].map((index) => (
              <button
                key={index}
                type="button"
                className={`dot ${activeDot === index ? "active" : ""}`}
                aria-label={`Rotate to position ${index + 1}`}
                aria-pressed={activeDot === index}
                onClick={() => handleDotClick(index)}
              />
            ))}
          </nav>

          {/* ── Tagline ── */}
          <p className="tagline">
            Turn scattered<br />
            documents into<br />
            <strong>connected knowledge.</strong>
          </p>

          {/* ── CTA row ── */}
          <div className="cta-row">
            <button className="cta" onClick={onEnterApp}>
              Start exploring
            </button>
            <span className="cta-line" />
            <span className="count" aria-hidden="true">07</span>
          </div>
        </div>
      </section>

      <section className="landing-section" id="features" aria-labelledby="features-heading">
        <div className="landing-section-inner">
          <p className="section-kicker">One workspace. A clearer trail.</p>
          <h2 id="features-heading">Make your documents useful.</h2>
          <p className="section-intro">
            Bring your files and questions together, then follow answers back to the information behind them.
          </p>
          <div className="landing-feature-grid">
            <article className="landing-feature-card">
              <span className="feature-index">01 / DOCUMENTS</span>
              <h3>Ask across your files</h3>
              <p>Upload PDF, DOCX, TXT, and Markdown files and ask questions in plain language.</p>
            </article>
            <article className="landing-feature-card">
              <span className="feature-index">02 / SOURCES</span>
              <h3>Keep answers traceable</h3>
              <p>Use document-aware retrieval to find relevant passages instead of searching files by hand.</p>
            </article>
            <article className="landing-feature-card">
              <span className="feature-index">03 / RESEARCH</span>
              <h3>Move from files to the web</h3>
              <p>Bring web search into the same workflow when a question needs information beyond your uploads.</p>
            </article>
          </div>
        </div>
      </section>

      <section className="landing-section landing-section--how" id="how" aria-labelledby="how-heading">
        <div className="landing-section-inner">
          <p className="section-kicker">A simple workflow</p>
          <h2 id="how-heading">From upload to understanding.</h2>
          <div className="landing-steps">
            <article className="landing-step">
              <span>01</span>
              <div><h3>Add your material</h3><p>Upload the documents you want to explore.</p></div>
            </article>
            <article className="landing-step">
              <span>02</span>
              <div><h3>Ask a real question</h3><p>Describe what you need to understand, compare, or find.</p></div>
            </article>
            <article className="landing-step">
              <span>03</span>
              <div><h3>Follow the trail</h3><p>Continue the conversation and use retrieved context to guide your next step.</p></div>
            </article>
          </div>
          <button type="button" className="section-cta" onClick={onEnterApp}>Start exploring <span aria-hidden="true">↗</span></button>
        </div>
      </section>
    </div>
  );
}
