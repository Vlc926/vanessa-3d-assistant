import * as THREE from 'three';

export class SpringDamper {
  constructor(stiffness = 190.0, damping = 14.0) {
    this.stiffness = stiffness;
    this.damping = damping;
    this.value = 0.0;
    this.velocity = 0.0;
    this.target = 0.0;
  }

  impulse(force) {
    this.velocity += Number(force) || 0.0;
  }

  step(dt) {
    const safeDt = Math.min(0.033, Math.max(0.001, dt));
    const displacement = this.value - this.target;
    const springForce = -this.stiffness * displacement;
    const dampingForce = -this.damping * this.velocity;
    const acceleration = springForce + dampingForce;
    this.velocity += acceleration * safeDt;
    this.value += this.velocity * safeDt;
    return this.value;
  }
}

export class PerlinNoise {
  constructor(seed = 42) {
    this.perm = new Uint8Array(512);
    const p = new Uint8Array(256);
    for (let i = 0; i < 256; i++) p[i] = i;
    let s = (seed % 2147483647) || 42;
    for (let i = 255; i > 0; i--) {
      s = (s * 16807) % 2147483647;
      const j = s % (i + 1);
      const tmp = p[i];
      p[i] = p[j];
      p[j] = tmp;
    }
    for (let i = 0; i < 512; i++) {
      this.perm[i] = p[i & 255];
    }
  }

  noise2D(x, y) {
    const X = Math.floor(x) & 255;
    const Y = Math.floor(y) & 255;
    const xf = x - Math.floor(x);
    const yf = y - Math.floor(y);
    const u = xf * xf * (3.0 - 2.0 * xf);
    const v = yf * yf * (3.0 - 2.0 * yf);
    const a = this.perm[X] + Y;
    const aa = this.perm[a];
    const ab = this.perm[a + 1];
    const b = this.perm[X + 1] + Y;
    const ba = this.perm[b];
    const bb = this.perm[b + 1];
    const grad = (hash, gx, gy) => {
      const h = hash & 3;
      const u1 = (h === 1 || h === 2) ? -gx : gx;
      const v1 = (h === 2 || h === 3) ? -gy : gy;
      return u1 + v1;
    };
    const x1 = THREE.MathUtils.lerp(grad(aa, xf, yf), grad(ba, xf - 1.0, yf), u);
    const x2 = THREE.MathUtils.lerp(grad(ab, xf, yf - 1.0), grad(bb, xf - 1.0, yf - 1.0), u);
    return THREE.MathUtils.lerp(x1, x2, v);
  }
}

export class SmartLocomotionRouter {
  static evaluateRoute(distancePx, urgency = 0.2, tone = 'relaxed', windowGaps = 0) {
    const dist = Math.max(0.0, Number(distancePx) || 0.0);
    const urg = Math.max(0.0, Math.min(1.0, Number(urgency) || 0.0));
    const toneLower = String(tone || 'relaxed').toLowerCase();
    const isUrgentTone = ['urgent', 'immediate', 'alert', 'panic', 'high', 'fast'].includes(toneLower);

    if (windowGaps > 0 && dist >= 300.0 && dist < 900.0 && !isUrgentTone && urg < 0.70) {
      return {
        mode: 'HYBRID_INTERLEAVED',
        anticipationSec: 0.06,
        transitionSec: 0.12,
        strideFreq: 2.4,
        clip: 'walk_forward'
      };
    }
    if (isUrgentTone || urg >= 0.70 || dist >= 650.0) {
      return {
        mode: 'TELEPORT_TRANSITION',
        anticipationSec: 0.08,
        transitionSec: 0.12,
        strideFreq: 3.2,
        clip: 'jump'
      };
    }
    const mode = (dist < 420.0 && urg < 0.45) ? 'WALK' : 'JOG';
    return {
      mode,
      anticipationSec: 0.0,
      transitionSec: Math.max(0.35, dist / (mode === 'WALK' ? 165.0 : 240.0)),
      strideFreq: mode === 'WALK' ? 1.85 : 2.65,
      clip: 'walk_forward'
    };
  }
}

export class AnimationEngine {
  constructor() {
    this.avatar = null;
    this.facialDriver = null;
    this.cognitiveState = 'IDLE';
    this.physicalState = 'GROUNDED';

    this.breathTime = 0.0;
    this.breathFreq = 0.24;

    this.idleTime = 0.0;
    this.blinkTimer = 3.0;
    this.isBlinking = false;
    this.blinkElapsed = 0.0;
    this.blinkDuration = 0.16;
    this.isDoubleBlink = false;
    this.doubleBlinkPending = false;
    this.doubleBlinkGapTimer = 0.0;

    this.perlin = new PerlinNoise(Math.floor(Math.random() * 65535));
    this.perlinSeed = Math.random() * 100.0;

    this.targetEmotion = {
      joy: 0.0,
      curiosity: 0.0,
      surprise: 0.0,
      tension: 0.0,
      confidence: 0.5,
      shyness: 0.0
    };
    this.currentEmotion = {
      joy: 0.0,
      curiosity: 0.0,
      surprise: 0.0,
      tension: 0.0,
      confidence: 0.5,
      shyness: 0.0
    };

    this.activeGesture = 'idle';
    this.gestureWeight = 0.0;
    this.gestureTime = 0.0;
    this.gestureDuration = 3.0;

    this.lookTarget = new THREE.Vector3(0, 0, 3.0);
    this.currentTargetPos = new THREE.Vector3(0, 0, 3.0);
    this.headYaw = 0.0;
    this.headPitch = 0.0;
    this.headRoll = 0.0;

    this.audioContext = null;
    this.analyser = null;
    this.audioSource = null;
    this.audioFreqData = null;
    this.isAudioPlaying = false;
    this.audioEnergySmooth = 0.0;
    this.visemeWeights = { aa: 0.0, ih: 0.0, ou: 0.0, ee: 0.0, oh: 0.0 };

    this.torsoSpring = new SpringDamper(210.0, 13.5);
    this.hipsSpring = new SpringDamper(195.0, 14.0);
    this.limbsSpring = new SpringDamper(220.0, 15.0);

    this.locomotionSpeedPx = 0.0;
    this.locomotionVx = 0.0;
    this.locomotionVy = 0.0;
    this.stridePhase = 0.0;
    this.isWindowMoving = false;
    this.teleportPhaseTimer = 0.0;
    this.teleportMode = null;

    this.dragAirTime = 0.0;
    this.freeFallVelocityY = 0.0;
    this.landingTimer = 0.0;
    this.headpatActive = false;
    this.headpatTimer = 0.0;
    this.windowPanicActive = false;
    this.perchStyle = 'none';

    this.fullBodyArticulation = null;
    this.learnedBehaviors = [];
    this.activeLearnedBehavior = null;
    this.onSaveLearnedBehavior = null;
    this._loadLearnedBehaviors();
  }

  _loadLearnedBehaviors() {
    if (typeof fetch !== 'function') return;
    fetch('/config/learned_behaviors.json')
      .then((res) => (res && res.ok ? res.json() : null))
      .then((data) => {
        if (data && Array.isArray(data.learned_expressions)) {
          this.learnedBehaviors = data.learned_expressions;
        }
      })
      .catch(() => {});
  }

  setAvatar(avatar) {
    this.avatar = avatar;
    if (avatar && avatar.profile) {
      this.torsoSpring.stiffness = avatar.profile.springStiffness || 210.0;
      this.torsoSpring.damping = avatar.profile.springDamping || 14.5;
    }
    this.torsoSpring.impulse(0.35);
    this.hipsSpring.impulse(0.25);
  }

  setFacialDriver(driver) {
    this.facialDriver = driver;
  }

  setDirective(directive) {
    if (!directive || typeof directive !== 'object') return;
    if (directive.state) {
      this.cognitiveState = String(directive.state).toUpperCase();
      this.torsoSpring.impulse(0.42);
      this.hipsSpring.impulse(0.30);
    }
    if (directive.emotion_vector) {
      for (const [k, v] of Object.entries(directive.emotion_vector)) {
        if (k in this.targetEmotion) {
          this.targetEmotion[k] = Math.max(0.0, Math.min(1.0, Number(v) || 0.0));
        }
      }
      this.limbsSpring.impulse(0.38);
    }
    if (directive.full_body_articulation) {
      this.fullBodyArticulation = directive.full_body_articulation;
    }
    if (directive.locomotion_route) {
      this.applyLocomotionRoute(directive.locomotion_route);
    }
    if (directive.learned_behaviors && Array.isArray(directive.learned_behaviors)) {
      this.learnedBehaviors = directive.learned_behaviors;
    }
    if (directive.body_gesture) {
      this.playGesture(directive.body_gesture, 3.2);
    }
    if (directive.look_target) {
      if (directive.look_target === 'user_camera') {
        this.lookTarget.set(0, 0, 3.0);
      } else if (directive.look_target === 'away_thoughtful') {
        this.lookTarget.set(0.6, 0.4, 2.5);
      }
    }
    if (directive.audio_base64 && typeof directive.audio_base64 === 'string') {
      this.playAudioBase64(directive.audio_base64);
    }
    this.synthesizeAndLearnBehavior(directive);
  }

  synthesizeAndLearnBehavior(directive) {
    if (!directive || (!directive.emotion_vector && !directive.dialogue_text)) return null;
    const emo = this.targetEmotion;
    const id = `synth_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
    const synthesized = {
      id,
      context: String(directive.state || 'SPEAKING').toLowerCase(),
      morphs: {
        happy: Number((emo.joy * 0.85 + emo.confidence * 0.15).toFixed(3)),
        surprised: Number((emo.surprise * 0.80 + emo.curiosity * 0.35).toFixed(3)),
        relaxed: Number((emo.confidence * 0.55).toFixed(3)),
        shy: Number((emo.shyness * 0.90).toFixed(3))
      },
      secondary_bones: {
        jawOpen: Number((emo.surprise * 0.14).toFixed(3)),
        pupilScale: Number((1.0 + emo.curiosity * 0.15 - emo.tension * 0.10).toFixed(3)),
        browAsymmetry: Number(((emo.curiosity - emo.tension) * 0.12).toFixed(3))
      },
      body_posture: {
        spinePitch: Number((emo.curiosity * 0.08 - emo.surprise * 0.06 + emo.shyness * 0.04).toFixed(3)),
        headTiltZ: Number(((emo.curiosity * 0.11) * (Math.random() > 0.5 ? 1 : -1)).toFixed(3)),
        shoulderLift: Number((emo.surprise * 0.05 + emo.shyness * 0.04).toFixed(3)),
        clip: directive.body_gesture || 'talking'
      }
    };
    this.activeLearnedBehavior = synthesized;
    this.learnedBehaviors.push(synthesized);
    if (this.learnedBehaviors.length > 120) {
      this.learnedBehaviors.shift();
    }
    if (typeof this.onSaveLearnedBehavior === 'function') {
      this.onSaveLearnedBehavior(synthesized);
    }
    return synthesized;
  }

  applyLocomotionRoute(route) {
    if (!route) return;
    const mode = route.locomotion_mode || route.mode || 'WALK';
    this.teleportMode = mode;
    if (mode === 'TELEPORT_TRANSITION' || mode === 'HYBRID_INTERLEAVED') {
      this.teleportPhaseTimer = (route.anticipation_sec || 0.08) + (route.transition_sec || 0.12);
      this.torsoSpring.impulse(-1.35);
      this.hipsSpring.impulse(-1.20);
      this.limbsSpring.impulse(0.95);
    }
  }

  syncLocomotionStep(x, y, vx, vy, stridePhase) {
    this.locomotionVx = Number(vx) || 0.0;
    this.locomotionVy = Number(vy) || 0.0;
    this.locomotionSpeedPx = Math.hypot(this.locomotionVx, this.locomotionVy);
    this.isWindowMoving = this.locomotionSpeedPx > 1.5;
    if (stridePhase !== undefined && stridePhase !== null) {
      this.stridePhase = Number(stridePhase);
    }
  }

  setPhysicalState(state, options = {}) {
    const prev = this.physicalState;
    this.physicalState = String(state || 'GROUNDED').toUpperCase();
    if (this.physicalState === 'DRAGGED_IN_AIR') {
      this.dragAirTime = 0.0;
      this.torsoSpring.impulse(0.85);
    } else if (this.physicalState === 'FREE_FALL') {
      this.freeFallVelocityY = Number(options.vy) || 250.0;
    } else if (this.physicalState === 'GROUNDED' && prev === 'FREE_FALL') {
      this.landingTimer = 0.42;
      this.torsoSpring.impulse(-1.65);
      this.hipsSpring.impulse(-1.80);
      this.limbsSpring.impulse(-1.20);
    } else if (this.physicalState === 'PERCHED') {
      this.perchStyle = options.style || 'sit';
    }
  }

  triggerHeadpat(active = true) {
    this.headpatActive = Boolean(active);
    if (this.headpatActive) {
      this.headpatTimer = 2.8;
      this.targetEmotion.joy = 0.92;
      this.targetEmotion.shyness = 0.55;
      this.torsoSpring.impulse(0.45);
    }
  }

  triggerWindowClosePanic(active = true) {
    this.windowPanicActive = Boolean(active);
    if (this.windowPanicActive) {
      this.targetEmotion.surprise = 0.95;
      this.targetEmotion.tension = 0.85;
      this.playGesture('shock', 2.4);
      this.torsoSpring.impulse(1.25);
    }
  }

  playGesture(name, duration = 3.0) {
    this.activeGesture = String(name || 'idle').toLowerCase();
    this.gestureDuration = Math.max(0.5, Number(duration) || 3.0);
    this.gestureTime = 0.0;
    this.gestureWeight = 0.0;
    this.limbsSpring.impulse(0.55);
  }

  playAudioBase64(b64) {
    if (!b64 || b64.length < 20) return;
    try {
      if (!this.audioContext) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        this.audioContext = new AudioCtx();
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 512;
        this.analyser.smoothingTimeConstant = 0.45;
        this.audioFreqData = new Uint8Array(this.analyser.frequencyBinCount);
      }
      if (this.audioContext.state === 'suspended') {
        this.audioContext.resume();
      }

      const binaryStr = atob(b64);
      const len = binaryStr.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryStr.charCodeAt(i);
      }

      this.audioContext.decodeAudioData(bytes.buffer, (buffer) => {
        if (this.audioSource) {
          try { this.audioSource.stop(); } catch (e) {}
        }
        this.audioSource = this.audioContext.createBufferSource();
        this.audioSource.buffer = buffer;
        this.audioSource.connect(this.analyser);
        this.analyser.connect(this.audioContext.destination);
        this.audioSource.onended = () => {
          this.isAudioPlaying = false;
          if (this.cognitiveState === 'SPEAKING') {
            this.cognitiveState = 'IDLE';
          }
        };
        this.isAudioPlaying = true;
        this.audioSource.start(0);
      }, () => {});
    } catch (e) {}
  }

  update(dt) {
    if (!this.avatar) return;
    const clampedDt = Math.min(0.045, dt);

    this._updateLayer4Expressions(clampedDt);
    this._updateLayer4LipSync(clampedDt);
    this._updateLayer0Idle(clampedDt);
    this._updateLayer1Cognitive(clampedDt);
    this._updateLayer2Gestures(clampedDt);
    this._updateLocomotionAndPhysicalStates(clampedDt);
    this._updateZZZSpringSquashStretch(clampedDt);
    this._updateLayer3LookAtIK(clampedDt);

    this.avatar.update(clampedDt);
  }

  _updateZZZSpringSquashStretch(dt) {
    const springTorso = this.torsoSpring.step(dt);
    const springHips = this.hipsSpring.step(dt);
    const springLimbs = this.limbsSpring.step(dt);

    const intensity = (this.avatar && this.avatar.profile) ? (this.avatar.profile.squashStretchIntensity || 0.55) : 0.55;
    const spine = this.avatar.getBone('spine');
    const chest = this.avatar.getBone('chest');
    const hips = this.avatar.getBone('hips');

    if (spine && spine.scale) {
      const sy = THREE.MathUtils.clamp(1.0 + springTorso * 0.08 * intensity, 0.88, 1.14);
      const sxz = THREE.MathUtils.clamp(1.0 / Math.sqrt(sy), 0.90, 1.12);
      spine.scale.set(sxz, sy, sxz);
    }
    if (chest && chest.scale) {
      const sy = THREE.MathUtils.clamp(1.0 + springTorso * 0.06 * intensity, 0.90, 1.12);
      const sxz = THREE.MathUtils.clamp(1.0 / Math.sqrt(sy), 0.92, 1.10);
      chest.scale.set(sxz, sy, sxz);
    }
    if (hips && hips.scale) {
      const sy = THREE.MathUtils.clamp(1.0 + springHips * 0.07 * intensity, 0.88, 1.12);
      const sxz = THREE.MathUtils.clamp(1.0 / Math.sqrt(sy), 0.90, 1.12);
      hips.scale.set(sxz, sy, sxz);
    }
    if (Math.abs(springLimbs) > 0.002) {
      const lArm = this.avatar.getBone('leftUpperArm');
      const rArm = this.avatar.getBone('rightUpperArm');
      if (lArm) lArm.rotation.z -= springLimbs * 0.04 * intensity;
      if (rArm) rArm.rotation.z += springLimbs * 0.04 * intensity;
    }
  }

  _updateLocomotionAndPhysicalStates(dt) {
    const hips = this.avatar.getBone('hips');
    const spine = this.avatar.getBone('spine');
    const lUpperLeg = this.avatar.getBone('leftUpperLeg');
    const rUpperLeg = this.avatar.getBone('rightUpperLeg');
    const lLowerLeg = this.avatar.getBone('leftLowerLeg');
    const rLowerLeg = this.avatar.getBone('rightLowerLeg');
    const lFoot = this.avatar.getBone('leftFoot');
    const rFoot = this.avatar.getBone('rightFoot');
    const lArm = this.avatar.getBone('leftUpperArm');
    const rArm = this.avatar.getBone('rightUpperArm');
    const lForearm = this.avatar.getBone('leftLowerArm');
    const rForearm = this.avatar.getBone('rightLowerArm');

    if (this.headpatActive) {
      this.headpatTimer -= dt;
      this.avatar.setExpression('blink', 0.95);
      this.avatar.setExpression('joy', 0.90);
      const head = this.avatar.getBone('head');
      if (head) {
        head.rotation.z = THREE.MathUtils.damp(head.rotation.z, Math.sin(this.idleTime * 6.0) * 0.14, 8.0, dt);
        head.rotation.x = THREE.MathUtils.damp(head.rotation.x, 0.08, 8.0, dt);
      }
      if (this.headpatTimer <= 0.0) {
        this.headpatActive = false;
      }
    }

    if (this.physicalState === 'DRAGGED_IN_AIR') {
      this.dragAirTime += dt;
      const kick = Math.sin(this.dragAirTime * 14.0);
      if (lUpperLeg) lUpperLeg.rotation.x = THREE.MathUtils.damp(lUpperLeg.rotation.x, -0.35 + kick * 0.45, 12.0, dt);
      if (rUpperLeg) rUpperLeg.rotation.x = THREE.MathUtils.damp(rUpperLeg.rotation.x, -0.35 - kick * 0.45, 12.0, dt);
      if (lLowerLeg) lLowerLeg.rotation.x = THREE.MathUtils.damp(lLowerLeg.rotation.x, 0.55 + Math.max(0, kick) * 0.40, 12.0, dt);
      if (rLowerLeg) rLowerLeg.rotation.x = THREE.MathUtils.damp(rLowerLeg.rotation.x, 0.55 + Math.max(0, -kick) * 0.40, 12.0, dt);
      if (lArm) {
        lArm.rotation.x = THREE.MathUtils.damp(lArm.rotation.x, 0.35, 10.0, dt);
        lArm.rotation.z = THREE.MathUtils.damp(lArm.rotation.z, -0.45, 10.0, dt);
      }
      if (rArm) {
        rArm.rotation.x = THREE.MathUtils.damp(rArm.rotation.x, 0.35, 10.0, dt);
        rArm.rotation.z = THREE.MathUtils.damp(rArm.rotation.z, 0.45, 10.0, dt);
      }
      if (lForearm) lForearm.rotation.x = THREE.MathUtils.damp(lForearm.rotation.x, 0.40, 10.0, dt);
      if (rForearm) rForearm.rotation.x = THREE.MathUtils.damp(rForearm.rotation.x, 0.40, 10.0, dt);
      this.avatar.setExpression('surprised', 0.85);
      this.avatar.setExpression('shy', 0.75);
      return;
    }

    if (this.physicalState === 'FREE_FALL') {
      if (lArm) lArm.rotation.z = THREE.MathUtils.damp(lArm.rotation.z, -0.25, 10.0, dt);
      if (rArm) rArm.rotation.z = THREE.MathUtils.damp(rArm.rotation.z, 0.25, 10.0, dt);
      if (lUpperLeg) lUpperLeg.rotation.x = THREE.MathUtils.damp(lUpperLeg.rotation.x, -0.25, 10.0, dt);
      if (rUpperLeg) rUpperLeg.rotation.x = THREE.MathUtils.damp(rUpperLeg.rotation.x, -0.15, 10.0, dt);
      if (lLowerLeg) lLowerLeg.rotation.x = THREE.MathUtils.damp(lLowerLeg.rotation.x, 0.45, 10.0, dt);
      if (rLowerLeg) rLowerLeg.rotation.x = THREE.MathUtils.damp(rLowerLeg.rotation.x, 0.35, 10.0, dt);
      this.avatar.setExpression('surprised', 0.95);
      return;
    }

    if (this.landingTimer > 0.0) {
      this.landingTimer = Math.max(0.0, this.landingTimer - dt);
      const comp = Math.sin((this.landingTimer / 0.42) * Math.PI);
      if (spine) spine.rotation.x = THREE.MathUtils.damp(spine.rotation.x, 0.28 * comp, 14.0, dt);
      if (lUpperLeg) lUpperLeg.rotation.x = THREE.MathUtils.damp(lUpperLeg.rotation.x, -0.55 * comp, 14.0, dt);
      if (rUpperLeg) rUpperLeg.rotation.x = THREE.MathUtils.damp(rUpperLeg.rotation.x, -0.55 * comp, 14.0, dt);
      if (lLowerLeg) lLowerLeg.rotation.x = THREE.MathUtils.damp(lLowerLeg.rotation.x, 0.95 * comp, 14.0, dt);
      if (rLowerLeg) rLowerLeg.rotation.x = THREE.MathUtils.damp(rLowerLeg.rotation.x, 0.95 * comp, 14.0, dt);
      return;
    }

    if (this.physicalState === 'PERCHED') {
      const swing = Math.sin(this.idleTime * 2.4) * 0.22;
      if (this.perchStyle === 'lie_down') {
        if (spine) spine.rotation.z = THREE.MathUtils.damp(spine.rotation.z, 0.45, 6.0, dt);
        if (lUpperLeg) lUpperLeg.rotation.x = THREE.MathUtils.damp(lUpperLeg.rotation.x, -0.40, 6.0, dt);
        if (rUpperLeg) rUpperLeg.rotation.x = THREE.MathUtils.damp(rUpperLeg.rotation.x, -0.30, 6.0, dt);
      } else {
        if (lUpperLeg) lUpperLeg.rotation.x = THREE.MathUtils.damp(lUpperLeg.rotation.x, -1.35, 8.0, dt);
        if (rUpperLeg) rUpperLeg.rotation.x = THREE.MathUtils.damp(rUpperLeg.rotation.x, -1.35, 8.0, dt);
        if (lLowerLeg) lLowerLeg.rotation.x = THREE.MathUtils.damp(lLowerLeg.rotation.x, 1.25 + swing, 8.0, dt);
        if (rLowerLeg) rLowerLeg.rotation.x = THREE.MathUtils.damp(rLowerLeg.rotation.x, 1.25 - swing, 8.0, dt);
      }
      return;
    }

    if (this.isWindowMoving) {
      const speedRatio = Math.min(2.2, Math.max(0.6, this.locomotionSpeedPx / 160.0));
      this.stridePhase += dt * 5.6 * speedRatio;
      const stride = Math.sin(this.stridePhase);
      const oppStride = Math.sin(this.stridePhase + Math.PI);

      if (lUpperLeg) lUpperLeg.rotation.x = THREE.MathUtils.damp(lUpperLeg.rotation.x, stride * 0.46, 14.0, dt);
      if (rUpperLeg) rUpperLeg.rotation.x = THREE.MathUtils.damp(rUpperLeg.rotation.x, oppStride * 0.46, 14.0, dt);
      if (lLowerLeg) lLowerLeg.rotation.x = THREE.MathUtils.damp(lLowerLeg.rotation.x, Math.max(0.05, -stride * 0.62), 14.0, dt);
      if (rLowerLeg) rLowerLeg.rotation.x = THREE.MathUtils.damp(rLowerLeg.rotation.x, Math.max(0.05, -oppStride * 0.62), 14.0, dt);
      if (lFoot) lFoot.rotation.x = THREE.MathUtils.damp(lFoot.rotation.x, stride * 0.22, 14.0, dt);
      if (rFoot) rFoot.rotation.x = THREE.MathUtils.damp(rFoot.rotation.x, oppStride * 0.22, 14.0, dt);
      if (lArm) lArm.rotation.x = THREE.MathUtils.damp(lArm.rotation.x, oppStride * 0.32, 12.0, dt);
      if (rArm) rArm.rotation.x = THREE.MathUtils.damp(rArm.rotation.x, stride * 0.32, 12.0, dt);
      if (hips) hips.rotation.y = THREE.MathUtils.damp(hips.rotation.y, stride * 0.06, 12.0, dt);
    }
  }

  _updateLayer0Idle(dt) {
    this.breathTime += dt * this.breathFreq * Math.PI * 2.0;
    this.idleTime += dt;

    const breath = Math.sin(this.breathTime);
    const deepBreath = Math.sin(this.breathTime * 0.5) * 0.015;

    const noiseSpine = this.perlin.noise2D(this.perlinSeed, this.idleTime * 0.35) * 0.025;
    const noiseArmL = this.perlin.noise2D(this.perlinSeed + 10.0, this.idleTime * 0.45) * 0.035;
    const noiseArmR = this.perlin.noise2D(this.perlinSeed + 20.0, this.idleTime * 0.45) * 0.035;
    const noiseHandL = this.perlin.noise2D(this.perlinSeed + 30.0, this.idleTime * 0.60) * 0.040;
    const noiseHandR = this.perlin.noise2D(this.perlinSeed + 40.0, this.idleTime * 0.60) * 0.040;

    const spine = this.avatar.getBone('spine');
    const chest = this.avatar.getBone('chest');
    const lShoulder = this.avatar.getBone('leftShoulder');
    const rShoulder = this.avatar.getBone('rightShoulder');
    const hips = this.avatar.getBone('hips');
    const lUpperArm = this.avatar.getBone('leftUpperArm');
    const rUpperArm = this.avatar.getBone('rightUpperArm');
    const lHand = this.avatar.getBone('leftHand');
    const rHand = this.avatar.getBone('rightHand');
    const lUpperLeg = this.avatar.getBone('leftUpperLeg');
    const rUpperLeg = this.avatar.getBone('rightUpperLeg');
    const lLowerLeg = this.avatar.getBone('leftLowerLeg');
    const rLowerLeg = this.avatar.getBone('rightLowerLeg');

    const fb = this.fullBodyArticulation;
    const extraSpinePitch = fb && fb.spine ? (fb.spine.pitch || 0.0) : 0.0;
    const extraChestPitch = fb && fb.chest ? (fb.chest.pitch || 0.0) : 0.0;
    const extraKneeFlex = fb && fb.legs ? (fb.legs.knee_flex || 0.05) : 0.05;

    const hipSway = Math.sin(this.idleTime * 0.85) * 0.024;
    const contrappostoRoll = -hipSway * 0.65;

    if (spine) {
      spine.rotation.x = THREE.MathUtils.damp(spine.rotation.x, breath * 0.022 + deepBreath + extraSpinePitch, 6.0, dt);
      spine.rotation.z = THREE.MathUtils.damp(spine.rotation.z, noiseSpine + contrappostoRoll * 0.5, 4.0, dt);
      spine.rotation.y = THREE.MathUtils.damp(spine.rotation.y, Math.sin(this.idleTime * 0.5) * 0.015, 3.5, dt);
    }
    if (chest) {
      chest.rotation.x = THREE.MathUtils.damp(chest.rotation.x, breath * 0.038 + deepBreath * 1.5 + extraChestPitch, 6.0, dt);
      chest.rotation.z = THREE.MathUtils.damp(chest.rotation.z, contrappostoRoll, 4.0, dt);
    }
    if (lShoulder) {
      lShoulder.rotation.z = THREE.MathUtils.damp(lShoulder.rotation.z, -0.04 + breath * 0.018 - contrappostoRoll * 0.4, 5.0, dt);
      lShoulder.rotation.y = THREE.MathUtils.damp(lShoulder.rotation.y, noiseArmL * 0.5, 4.0, dt);
    }
    if (rShoulder) {
      rShoulder.rotation.z = THREE.MathUtils.damp(rShoulder.rotation.z, 0.04 - breath * 0.018 - contrappostoRoll * 0.4, 5.0, dt);
      rShoulder.rotation.y = THREE.MathUtils.damp(rShoulder.rotation.y, -noiseArmR * 0.5, 4.0, dt);
    }
    if (hips) {
      hips.rotation.z = THREE.MathUtils.damp(hips.rotation.z, hipSway, 4.0, dt);
      hips.rotation.y = THREE.MathUtils.damp(hips.rotation.y, hipSway * 0.6, 4.0, dt);
    }

    if (this.gestureWeight <= 0.001 && !this.isWindowMoving && this.physicalState === 'GROUNDED') {
      if (lUpperArm) {
        lUpperArm.rotation.z = THREE.MathUtils.damp(lUpperArm.rotation.z, -0.72 + noiseArmL, 4.0, dt);
        lUpperArm.rotation.x = THREE.MathUtils.damp(lUpperArm.rotation.x, 0.05 + breath * 0.012, 4.0, dt);
      }
      if (rUpperArm) {
        rUpperArm.rotation.z = THREE.MathUtils.damp(rUpperArm.rotation.z, 0.72 - noiseArmR, 4.0, dt);
        rUpperArm.rotation.x = THREE.MathUtils.damp(rUpperArm.rotation.x, 0.05 + breath * 0.012, 4.0, dt);
      }
      if (lHand) {
        lHand.rotation.z = THREE.MathUtils.damp(lHand.rotation.z, noiseHandL, 5.0, dt);
        lHand.rotation.x = THREE.MathUtils.damp(lHand.rotation.x, noiseHandL * 0.6, 5.0, dt);
      }
      if (rHand) {
        rHand.rotation.z = THREE.MathUtils.damp(rHand.rotation.z, -noiseHandR, 5.0, dt);
        rHand.rotation.x = THREE.MathUtils.damp(rHand.rotation.x, noiseHandR * 0.6, 5.0, dt);
      }
    }

    if (!this.isWindowMoving && this.physicalState === 'GROUNDED') {
      if (lUpperLeg) lUpperLeg.rotation.x = THREE.MathUtils.damp(lUpperLeg.rotation.x, -extraKneeFlex * 0.5, 5.0, dt);
      if (rUpperLeg) rUpperLeg.rotation.x = THREE.MathUtils.damp(rUpperLeg.rotation.x, -extraKneeFlex * 0.5, 5.0, dt);
      if (lLowerLeg) lLowerLeg.rotation.x = THREE.MathUtils.damp(lLowerLeg.rotation.x, extraKneeFlex, 5.0, dt);
      if (rLowerLeg) rLowerLeg.rotation.x = THREE.MathUtils.damp(rLowerLeg.rotation.x, extraKneeFlex, 5.0, dt);
    }

    this._updateStochasticBlink(dt);
  }

  _updateStochasticBlink(dt) {
    if (this.headpatActive) return;

    if (this.doubleBlinkPending) {
      this.doubleBlinkGapTimer -= dt;
      if (this.doubleBlinkGapTimer <= 0.0) {
        this.doubleBlinkPending = false;
        this.isBlinking = true;
        this.blinkElapsed = 0.0;
        this.blinkDuration = 0.14;
      }
      return;
    }

    this.blinkTimer -= dt;
    if (this.blinkTimer <= 0.0 && !this.isBlinking) {
      if (this.currentEmotion.joy < 0.70) {
        this.isBlinking = true;
        this.blinkElapsed = 0.0;
        this.blinkDuration = 0.15;
        this.isDoubleBlink = Math.random() < 0.16;
      } else {
        this.blinkTimer = 2.2 + Math.random() * 2.8;
      }
    }

    if (this.isBlinking) {
      this.blinkElapsed += dt;
      const progress = this.blinkElapsed / this.blinkDuration;
      let blinkVal = 0.0;
      if (progress <= 0.35) {
        blinkVal = progress / 0.35;
      } else if (progress <= 1.0) {
        const p = (progress - 0.35) / 0.65;
        blinkVal = 1.0 - Math.pow(p, 1.4);
      } else {
        this.isBlinking = false;
        blinkVal = 0.0;
        if (this.isDoubleBlink) {
          this.isDoubleBlink = false;
          this.doubleBlinkPending = true;
          this.doubleBlinkGapTimer = 0.11;
        } else {
          this.blinkTimer = 2.2 + Math.random() * 3.6;
        }
      }
      this.avatar.setExpression('blink', Math.max(0.0, Math.min(1.0, blinkVal)));
    }
  }

  _updateLayer1Cognitive(dt) {
    const head = this.avatar.getBone('head');
    const spine = this.avatar.getBone('spine');

    let targetSpinePitch = 0.0;
    let targetHeadTiltZ = 0.0;
    let targetHeadPitchX = 0.0;
    let targetHeadYawY = 0.0;

    if (this.cognitiveState === 'LISTENING') {
      targetSpinePitch = 0.085;
      targetHeadPitchX = -0.04;
      this.lookTarget.set(0.0, 0.05, 2.8);
    } else if (this.cognitiveState === 'THINKING') {
      targetHeadTiltZ = 0.087;
      targetHeadPitchX = 0.06;
      targetHeadYawY = -0.12;
      this.lookTarget.set(0.5, 0.45, 2.5);
      this.avatar.setExpression('shy', 0.15);
    } else if (this.cognitiveState === 'SPEAKING') {
      const speechBob = Math.sin(this.idleTime * 4.6) * 0.042;
      const speechSide = Math.sin(this.idleTime * 2.3) * 0.020;
      targetHeadPitchX = speechBob;
      targetHeadTiltZ = speechSide;
      this.lookTarget.set(0.0, 0.0, 2.8);
    }

    if (this.activeLearnedBehavior && this.activeLearnedBehavior.body_posture) {
      targetSpinePitch += this.activeLearnedBehavior.body_posture.spinePitch || 0.0;
      targetHeadTiltZ += this.activeLearnedBehavior.body_posture.headTiltZ || 0.0;
    }

    if (spine && (this.cognitiveState === 'LISTENING' || this.cognitiveState === 'THINKING' || this.activeLearnedBehavior)) {
      spine.rotation.x = THREE.MathUtils.damp(spine.rotation.x, targetSpinePitch, 5.0, dt);
    }
    if (head) {
      head.rotation.z = THREE.MathUtils.damp(head.rotation.z, targetHeadTiltZ, 5.0, dt);
      head.rotation.x = THREE.MathUtils.damp(head.rotation.x, targetHeadPitchX, 5.0, dt);
      head.rotation.y = THREE.MathUtils.damp(head.rotation.y, targetHeadYawY, 5.0, dt);
    }
  }

  _updateLayer2Gestures(dt) {
    this.gestureTime += dt;
    const progress = Math.min(1.0, this.gestureTime / this.gestureDuration);
    if (progress <= 0.18) {
      const p = progress / 0.18;
      const easeIn = p * p * (3.0 - 2.0 * p);
      this.gestureWeight = THREE.MathUtils.damp(this.gestureWeight, easeIn, 12.0, dt);
    } else if (progress <= 0.82) {
      this.gestureWeight = 1.0;
    } else if (progress < 1.0) {
      const p = (1.0 - progress) / 0.18;
      const easeOut = p * p * (3.0 - 2.0 * p);
      this.gestureWeight = THREE.MathUtils.damp(this.gestureWeight, easeOut, 10.0, dt);
    } else {
      this.gestureWeight = 0.0;
      this.activeGesture = 'idle';
    }

    const lArm = this.avatar.getBone('leftUpperArm');
    const rArm = this.avatar.getBone('rightUpperArm');
    const lForearm = this.avatar.getBone('leftLowerArm');
    const rForearm = this.avatar.getBone('rightLowerArm');
    const lShoulder = this.avatar.getBone('leftShoulder');
    const rShoulder = this.avatar.getBone('rightShoulder');

    if (this.gestureWeight <= 0.001) {
      if (!this.isWindowMoving && this.physicalState === 'GROUNDED') {
        if (lArm) lArm.rotation.z = THREE.MathUtils.damp(lArm.rotation.z, -0.70, 5.0, dt);
        if (rArm) rArm.rotation.z = THREE.MathUtils.damp(rArm.rotation.z, 0.70, 5.0, dt);
        if (lForearm) lForearm.rotation.x = THREE.MathUtils.damp(lForearm.rotation.x, 0.21, 5.0, dt);
        if (rForearm) rForearm.rotation.x = THREE.MathUtils.damp(rForearm.rotation.x, 0.21, 5.0, dt);
      }
      return;
    }
    const w = this.gestureWeight;

    if (this.activeGesture === 'explain_open_hands') {
      if (lShoulder) lShoulder.rotation.z = THREE.MathUtils.damp(lShoulder.rotation.z, -0.06 * w, 6.0, dt);
      if (rShoulder) rShoulder.rotation.z = THREE.MathUtils.damp(rShoulder.rotation.z, 0.06 * w, 6.0, dt);
      if (lArm) {
        lArm.rotation.x = THREE.MathUtils.damp(lArm.rotation.x, -0.35 * w, 6.0, dt);
        lArm.rotation.z = THREE.MathUtils.damp(lArm.rotation.z, -0.65 * w, 6.0, dt);
      }
      if (rArm) {
        rArm.rotation.x = THREE.MathUtils.damp(rArm.rotation.x, -0.35 * w, 6.0, dt);
        rArm.rotation.z = THREE.MathUtils.damp(rArm.rotation.z, 0.65 * w, 6.0, dt);
      }
      if (lForearm) lForearm.rotation.x = THREE.MathUtils.damp(lForearm.rotation.x, 0.60 * w, 6.0, dt);
      if (rForearm) rForearm.rotation.x = THREE.MathUtils.damp(rForearm.rotation.x, 0.60 * w, 6.0, dt);
    } else if (this.activeGesture === 'nod') {
      const head = this.avatar.getBone('head');
      if (head) {
        head.rotation.x = THREE.MathUtils.damp(head.rotation.x, Math.sin(this.gestureTime * 7.5) * 0.16 * w, 8.0, dt);
      }
    } else if (this.activeGesture === 'greet' || this.activeGesture === 'wave') {
      if (rShoulder) rShoulder.rotation.z = THREE.MathUtils.damp(rShoulder.rotation.z, 0.08 * w, 6.0, dt);
      if (rArm) {
        rArm.rotation.x = THREE.MathUtils.damp(rArm.rotation.x, -0.85 * w, 6.0, dt);
        rArm.rotation.z = THREE.MathUtils.damp(rArm.rotation.z, -0.55 * w, 6.0, dt);
      }
      if (rForearm) {
        rForearm.rotation.x = THREE.MathUtils.damp(rForearm.rotation.x, 0.85 * w, 6.0, dt);
        rForearm.rotation.z = THREE.MathUtils.damp(rForearm.rotation.z, Math.sin(this.gestureTime * 8.0) * 0.28 * w, 8.0, dt);
      }
    } else if (this.activeGesture === 'think_pose') {
      if (rArm) {
        rArm.rotation.x = THREE.MathUtils.damp(rArm.rotation.x, -0.55 * w, 6.0, dt);
        rArm.rotation.z = THREE.MathUtils.damp(rArm.rotation.z, -0.50 * w, 6.0, dt);
      }
      if (rForearm) {
        rForearm.rotation.x = THREE.MathUtils.damp(rForearm.rotation.x, 1.15 * w, 6.0, dt);
        rForearm.rotation.y = THREE.MathUtils.damp(rForearm.rotation.y, 0.35 * w, 6.0, dt);
      }
    } else if (this.activeGesture === 'shock') {
      if (lShoulder) lShoulder.rotation.z = THREE.MathUtils.damp(lShoulder.rotation.z, -0.09 * w, 10.0, dt);
      if (rShoulder) rShoulder.rotation.z = THREE.MathUtils.damp(rShoulder.rotation.z, 0.09 * w, 10.0, dt);
      if (lArm) lArm.rotation.z = THREE.MathUtils.damp(lArm.rotation.z, -0.30 * w, 10.0, dt);
      if (rArm) rArm.rotation.z = THREE.MathUtils.damp(rArm.rotation.z, 0.30 * w, 10.0, dt);
      if (lForearm) lForearm.rotation.x = THREE.MathUtils.damp(lForearm.rotation.x, 0.90 * w, 10.0, dt);
      if (rForearm) rForearm.rotation.x = THREE.MathUtils.damp(rForearm.rotation.x, 0.90 * w, 10.0, dt);
    }
  }

  _updateLayer3LookAtIK(dt) {
    this.currentTargetPos.lerp(this.lookTarget, Math.min(1.0, dt * 4.5));

    const head = this.avatar.getBone('head');
    const neck = this.avatar.getBone('neck');
    if (!head) return;

    const headWorldPos = new THREE.Vector3();
    head.getWorldPosition(headWorldPos);

    const dir = new THREE.Vector3().subVectors(this.currentTargetPos, headWorldPos).normalize();
    let targetYaw = Math.atan2(dir.x, dir.z);
    let targetPitch = -Math.asin(Math.max(-1.0, Math.min(1.0, dir.y)));

    targetYaw = THREE.MathUtils.clamp(targetYaw, -0.523, 0.523);
    targetPitch = THREE.MathUtils.clamp(targetPitch, -0.349, 0.349);
    const targetRoll = THREE.MathUtils.clamp(-targetYaw * 0.15, -0.174, 0.174);

    this.headYaw = THREE.MathUtils.damp(this.headYaw, targetYaw, 5.0, dt);
    this.headPitch = THREE.MathUtils.damp(this.headPitch, targetPitch, 5.0, dt);
    this.headRoll = THREE.MathUtils.damp(this.headRoll, targetRoll, 5.0, dt);

    if (neck) {
      neck.rotation.y = THREE.MathUtils.damp(neck.rotation.y, this.headYaw * 0.35, 5.0, dt);
      neck.rotation.x = THREE.MathUtils.damp(neck.rotation.x, this.headPitch * 0.35, 5.0, dt);
    }
    head.rotation.y = THREE.MathUtils.damp(head.rotation.y, this.headYaw * 0.65, 5.0, dt);
    head.rotation.x = THREE.MathUtils.damp(head.rotation.x, this.headPitch * 0.65, 5.0, dt);
    head.rotation.z = THREE.MathUtils.damp(head.rotation.z, this.headRoll, 5.0, dt);
  }

  _updateLayer4Expressions(dt) {
    for (const [key, targetVal] of Object.entries(this.targetEmotion)) {
      this.currentEmotion[key] = THREE.MathUtils.damp(
        this.currentEmotion[key] || 0.0,
        targetVal,
        6.0,
        dt
      );
      if (this.facialDriver && typeof this.facialDriver.setMorph === 'function') {
        if (key === 'joy') {
          this.facialDriver.setMorph('happy', this.currentEmotion.joy);
        } else if (key === 'curiosity') {
          this.facialDriver.setMorph('surprised', this.currentEmotion.curiosity * 0.6);
        } else if (key === 'surprise') {
          this.facialDriver.setMorph('surprised', this.currentEmotion.surprise);
        } else if (key === 'tension') {
          this.facialDriver.setMorph('angry', this.currentEmotion.tension * 0.8);
        } else if (key === 'shyness') {
          this.facialDriver.setMorph('shy', this.currentEmotion.shyness);
        }
      } else {
        if (key === 'joy') {
          this.avatar.setExpression('joy', this.currentEmotion.joy);
        } else if (key === 'curiosity') {
          this.avatar.setExpression('surprised', this.currentEmotion.curiosity * 0.6);
        } else if (key === 'surprise') {
          this.avatar.setExpression('surprised', this.currentEmotion.surprise);
        } else if (key === 'tension') {
          this.avatar.setExpression('angry', this.currentEmotion.tension * 0.8);
        } else if (key === 'shyness') {
          this.avatar.setExpression('shy', this.currentEmotion.shyness);
        }
      }
    }
  }

  _updateLayer4LipSync(dt) {
    if (!this.isAudioPlaying || !this.analyser || !this.audioFreqData) {
      for (const v of ['aa', 'ih', 'ou', 'ee', 'oh']) {
        this.visemeWeights[v] = THREE.MathUtils.damp(this.visemeWeights[v], 0.0, 14.0, dt);
        if (this.facialDriver && typeof this.facialDriver.setViseme === 'function') {
          this.facialDriver.setViseme(v, this.visemeWeights[v]);
        } else {
          this.avatar.setViseme(v, this.visemeWeights[v]);
        }
      }
      return;
    }

    this.analyser.getByteFrequencyData(this.audioFreqData);
    const binCount = this.analyser.frequencyBinCount;
    const nyquist = (this.audioContext ? this.audioContext.sampleRate : 44100) / 2.0;
    const binHz = nyquist / binCount;

    const getEnergy = (minHz, maxHz) => {
      const startBin = Math.max(0, Math.floor(minHz / binHz));
      const endBin = Math.min(binCount - 1, Math.ceil(maxHz / binHz));
      let sum = 0;
      let count = 0;
      for (let i = startBin; i <= endBin; i++) {
        sum += this.audioFreqData[i];
        count++;
      }
      return count > 0 ? (sum / count) / 255.0 : 0.0;
    };

    const energyAa = getEnergy(700, 1200);
    const energyEe = (getEnergy(300, 500) + getEnergy(2000, 2600)) * 0.5;
    const energyIh = (getEnergy(400, 600) + getEnergy(1800, 2200)) * 0.5;
    const energyOh = getEnergy(400, 700);
    const energyOu = getEnergy(300, 450);

    const maxEnergy = Math.max(energyAa, energyEe, energyIh, energyOh, energyOu);
    const scale = maxEnergy > 0.08 ? 1.25 : 0.0;

    this.audioEnergySmooth = THREE.MathUtils.damp(this.audioEnergySmooth, maxEnergy, 10.0, dt);

    this.visemeWeights.aa = THREE.MathUtils.damp(this.visemeWeights.aa, energyAa * scale, 18.0, dt);
    this.visemeWeights.ee = THREE.MathUtils.damp(this.visemeWeights.ee, energyEe * scale, 18.0, dt);
    this.visemeWeights.ih = THREE.MathUtils.damp(this.visemeWeights.ih, energyIh * scale, 18.0, dt);
    this.visemeWeights.oh = THREE.MathUtils.damp(this.visemeWeights.oh, energyOh * scale, 18.0, dt);
    this.visemeWeights.ou = THREE.MathUtils.damp(this.visemeWeights.ou, energyOu * scale, 18.0, dt);

    for (const v of ['aa', 'ee', 'ih', 'oh', 'ou']) {
      if (this.facialDriver && typeof this.facialDriver.setViseme === 'function') {
        this.facialDriver.setViseme(v, this.visemeWeights[v]);
      } else {
        this.avatar.setViseme(v, this.visemeWeights[v]);
      }
    }
  }
}
