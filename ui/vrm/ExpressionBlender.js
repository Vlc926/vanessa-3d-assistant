import * as THREE from 'three';

export function easeOutBack(t, c1 = 1.70158) {
  const c3 = c1 + 1.0;
  const t1 = Math.max(0.0, Math.min(1.0, t)) - 1.0;
  return 1.0 + c3 * Math.pow(t1, 3) + c1 * Math.pow(t1, 2);
}

export function easeOutElastic(t) {
  if (t <= 0) return 0;
  if (t >= 1) return 1;
  const c4 = (2 * Math.PI) / 3;
  return Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1;
}

export class ExpressionBlender {
  constructor() {
    this.channels = new Map();
    this.activeEmotion = 'neutral';
    this.emotionIntensity = 1.0;
    this.transitionDuration = 0.32;

    this.visemes = {
      aa: 0.0,
      ih: 0.0,
      ou: 0.0,
      ee: 0.0,
      oh: 0.0
    };

    this.browAsymmetry = {
      left: 0.0,
      right: 0.0
    };

    this.cheekPuff = 0.0;
    this.blushOpacity = 0.0;
    this.targetBlushOpacity = 0.0;
    this.pupilScale = 1.0;
    this.targetPupilScale = 1.0;
    this.pupilOffset = new THREE.Vector2(0, 0);
    this.targetPupilOffset = new THREE.Vector2(0, 0);

    this.saccadeTimer = 0.0;
    this.saccadeInterval = 2.4;
    this.microJitter = new THREE.Vector2(0, 0);

    this.secondaryBoneState = {
      jawPitch: 0.0,
      jawForward: 0.0,
      leftCheekScale: 1.0,
      rightCheekScale: 1.0,
      tongueOut: 0.0,
      neckPitch: 0.0,
      neckYaw: 0.0,
      neckRoll: 0.0,
      headPitch: 0.0,
      headYaw: 0.0,
      headRoll: 0.0
    };

    this.targetSecondaryBoneState = {
      jawPitch: 0.0,
      jawForward: 0.0,
      leftCheekScale: 1.0,
      rightCheekScale: 1.0,
      tongueOut: 0.0,
      neckPitch: 0.0,
      neckYaw: 0.0,
      neckRoll: 0.0,
      headPitch: 0.0,
      headYaw: 0.0,
      headRoll: 0.0
    };

    this.presets = {
      neutral: {},
      happy: {
        happy: 0.85,
        joy: 0.85,
        relaxed: 0.35,
        Fcl_ALL_Joy: 0.85,
        Fcl_MTH_Joy: 0.70,
        Fcl_BRW_Joy: 0.40
      },
      surprised: {
        surprised: 0.95,
        aa: 0.35,
        Fcl_ALL_Surprised: 0.95,
        Fcl_EYE_Surprised: 0.90,
        Fcl_MTH_A: 0.35
      },
      shocked: {
        surprised: 1.0,
        aa: 0.60,
        blink: 0.0,
        Fcl_ALL_Surprised: 1.0,
        Fcl_MTH_A: 0.60
      },
      pout: {
        angry: 0.38,
        sad: 0.45,
        ou: 0.65,
        Fcl_MTH_U: 0.70,
        Fcl_BRW_Angry: 0.45
      },
      angry: {
        angry: 0.85,
        Fcl_ALL_Angry: 0.85,
        Fcl_BRW_Angry: 0.80,
        Fcl_MTH_Angry: 0.70
      },
      sad: {
        sad: 0.80,
        sorrow: 0.80,
        Fcl_ALL_Sorrow: 0.80,
        Fcl_BRW_Sorrow: 0.75
      },
      embarrassed: {
        happy: 0.30,
        sad: 0.35,
        shy: 0.85,
        blink: 0.25,
        Fcl_BRW_Sorrow: 0.35
      },
      shamed: {
        sad: 0.65,
        shy: 0.75,
        blink: 0.30,
        Fcl_BRW_Sorrow: 0.50
      },
      smug: {
        happy: 0.60,
        relaxed: 0.45,
        blinkLeft: 0.25,
        Fcl_MTH_Fun: 0.65,
        Fcl_EYE_Close_L: 0.28,
        Fcl_BRW_Joy: 0.45
      },
      winking: {
        blinkLeft: 1.0,
        blinkRight: 0.0,
        happy: 0.75,
        relaxed: 0.30,
        Fcl_EYE_Close_L: 1.0,
        Fcl_MTH_Joy: 0.75
      },
      cat_smile: {
        happy: 0.75,
        relaxed: 0.50,
        blinkLeft: 0.15,
        _mouthPress_CatMouth: 0.75
      },
      thinking: {
        surprised: 0.20,
        relaxed: 0.40,
        blinkRight: 0.20,
        Fcl_BRW_Joy: 0.35
      },
      dramatic_smirk: {
        happy: 0.70,
        blinkLeft: 0.35,
        relaxed: 0.45,
        Fcl_MTH_Fun: 0.80,
        Fcl_EYE_Close_L: 0.40
      },
      star_eyes: {
        surprised: 0.75,
        happy: 0.65,
        eyeWideLeft: 0.85,
        eyeWideRight: 0.85,
        Fcl_ALL_Joy: 0.75,
        Fcl_EYE_Surprised: 0.90,
        Fcl_BRW_Joy: 0.60
      },
      flustered: {
        relaxed: 0.45,
        shy: 0.90,
        cheekSquintLeft: 0.75,
        cheekSquintRight: 0.75,
        Fcl_BRW_Sorrow: 0.45
      }
    };
  }

  setEmotion(name, intensity = 1.0, duration = 0.32) {
    const norm = String(name || 'neutral').toLowerCase();
    this.activeEmotion = norm;
    this.emotionIntensity = Math.max(0.0, Math.min(1.0, Number(intensity) || 1.0));
    this.transitionDuration = Math.max(0.08, Number(duration) || 0.32);

    const preset = this.presets[norm] || this.presets.neutral;
    const activeKeys = new Set(Object.keys(preset));

    for (const [key, channel] of this.channels.entries()) {
      if (!key.startsWith('viseme_') && !key.startsWith('custom_') && !activeKeys.has(key)) {
        this.setMorph(key, 0.0, false, this.transitionDuration * 0.9);
      }
    }

    for (const [key, val] of Object.entries(preset)) {
      this.setMorph(key, val * this.emotionIntensity, false, this.transitionDuration);
    }

    this._updateContextualSecondaryBones(norm, this.emotionIntensity);
  }

  setCustomBlendshape(name, weight, duration = 0.30) {
    this.setMorph(`custom_${name}`, weight, false, duration);
  }

  setMorph(name, targetVal, snap = false, duration = 0.32) {
    const norm = String(name || '');
    if (!norm) return;
    const target = Math.max(0.0, Math.min(1.0, Number(targetVal) || 0.0));

    let ch = this.channels.get(norm);
    if (!ch) {
      ch = {
        current: target,
        target: target,
        startVal: target,
        elapsed: 1.0,
        duration: duration || 0.32,
        curve: 'easeOutBack'
      };
      this.channels.set(norm, ch);
    }

    if (snap) {
      ch.current = target;
      ch.target = target;
      ch.startVal = target;
      ch.elapsed = ch.duration;
      return;
    }

    if (Math.abs(ch.target - target) > 0.001) {
      ch.startVal = ch.current;
      ch.target = target;
      ch.elapsed = 0.0;
      ch.duration = Math.max(0.08, duration || 0.32);
    }
  }

  setViseme(name, weight) {
    const norm = String(name || '').toLowerCase();
    if (norm in this.visemes) {
      this.visemes[norm] = Math.max(0.0, Math.min(1.0, Number(weight) || 0.0));
      this.setMorph(`viseme_${norm}`, this.visemes[norm], false, 0.10);
    }
  }

  setBrowAsymmetry(left, right) {
    this.browAsymmetry.left = Math.max(-1.0, Math.min(1.0, Number(left) || 0.0));
    this.browAsymmetry.right = Math.max(-1.0, Math.min(1.0, Number(right) || 0.0));
  }

  setDecoupledGaze(x, y, instant = false) {
    const cx = Math.max(-0.6, Math.min(0.6, Number(x) || 0.0));
    const cy = Math.max(-0.4, Math.min(0.4, Number(y) || 0.0));
    this.targetPupilOffset.set(cx, cy);
    if (instant) {
      this.pupilOffset.copy(this.targetPupilOffset);
    }
  }

  _updateContextualSecondaryBones(emotion, factor) {
    const t = this.targetSecondaryBoneState;

    if (emotion === 'surprised' || emotion === 'shocked') {
      t.jawPitch = 0.22 * factor;
      t.jawForward = 0.0;
      t.leftCheekScale = 1.0;
      t.rightCheekScale = 1.0;
      t.neckPitch = -0.05 * factor;
      t.neckYaw = 0.0;
      t.neckRoll = 0.0;
      t.headPitch = -0.06 * factor;
      t.headYaw = 0.0;
      t.headRoll = 0.0;
      this.targetPupilScale = 1.15;
      this.targetBlushOpacity = 0.0;
      this.setBrowAsymmetry(0.35 * factor, 0.35 * factor);
    } else if (emotion === 'pout') {
      t.jawPitch = 0.05 * factor;
      t.jawForward = 0.015 * factor;
      t.leftCheekScale = 1.0 + 0.18 * factor;
      t.rightCheekScale = 1.0 + 0.18 * factor;
      t.neckPitch = 0.04 * factor;
      t.neckYaw = 0.0;
      t.neckRoll = 0.03 * factor;
      t.headPitch = 0.08 * factor;
      t.headYaw = 0.0;
      t.headRoll = 0.05 * factor;
      this.targetPupilScale = 0.95;
      this.targetBlushOpacity = 0.45 * factor;
      this.setBrowAsymmetry(-0.15 * factor, -0.15 * factor);
    } else if (emotion === 'happy') {
      t.jawPitch = 0.02 * factor;
      t.jawForward = 0.0;
      t.leftCheekScale = 1.0 + 0.08 * factor;
      t.rightCheekScale = 1.0 + 0.08 * factor;
      t.neckPitch = -0.02 * factor;
      t.neckYaw = 0.0;
      t.neckRoll = 0.02 * factor;
      t.headPitch = -0.02 * factor;
      t.headYaw = 0.0;
      t.headRoll = 0.04 * factor;
      this.targetPupilScale = 1.10;
      this.targetBlushOpacity = 0.25 * factor;
      this.setBrowAsymmetry(0.20 * factor, 0.20 * factor);
    } else if (emotion === 'shamed' || emotion === 'embarrassed') {
      t.jawPitch = 0.0;
      t.jawForward = 0.0;
      t.leftCheekScale = 1.0;
      t.rightCheekScale = 1.0;
      t.neckPitch = 0.08 * factor;
      t.neckYaw = 0.03 * factor;
      t.neckRoll = -0.04 * factor;
      t.headPitch = 0.12 * factor;
      t.headYaw = 0.05 * factor;
      t.headRoll = -0.05 * factor;
      this.targetPupilScale = 0.92;
      this.targetBlushOpacity = 0.85 * factor;
      this.setBrowAsymmetry(-0.10 * factor, -0.25 * factor);
    } else if (emotion === 'angry') {
      t.jawPitch = -0.02 * factor;
      t.jawForward = 0.0;
      t.leftCheekScale = 1.0;
      t.rightCheekScale = 1.0;
      t.neckPitch = 0.06 * factor;
      t.neckYaw = 0.0;
      t.neckRoll = 0.0;
      t.headPitch = 0.09 * factor;
      t.headYaw = 0.0;
      t.headRoll = 0.0;
      this.targetPupilScale = 0.82;
      this.targetBlushOpacity = 0.15 * factor;
      this.setBrowAsymmetry(-0.40 * factor, -0.40 * factor);
    } else if (emotion === 'smug' || emotion === 'dramatic_smirk') {
      t.jawPitch = 0.02 * factor;
      t.jawForward = 0.0;
      t.leftCheekScale = 1.0 + 0.05 * factor;
      t.rightCheekScale = 1.0;
      t.neckPitch = -0.03 * factor;
      t.neckYaw = 0.04 * factor;
      t.neckRoll = -0.06 * factor;
      t.headPitch = -0.04 * factor;
      t.headYaw = 0.06 * factor;
      t.headRoll = -0.08 * factor;
      this.targetPupilScale = 1.08;
      this.targetBlushOpacity = 0.10 * factor;
      this.setBrowAsymmetry(0.35 * factor, -0.25 * factor);
    } else if (emotion === 'thinking') {
      t.jawPitch = 0.0;
      t.jawForward = 0.0;
      t.leftCheekScale = 1.0;
      t.rightCheekScale = 1.0;
      t.neckPitch = -0.02 * factor;
      t.neckYaw = -0.05 * factor;
      t.neckRoll = 0.07 * factor;
      t.headPitch = -0.03 * factor;
      t.headYaw = -0.08 * factor;
      t.headRoll = 0.10 * factor;
      this.targetPupilScale = 1.02;
      this.targetBlushOpacity = 0.0;
      this.setBrowAsymmetry(0.25 * factor, -0.15 * factor);
    } else {
      t.jawPitch = 0.0;
      t.jawForward = 0.0;
      t.leftCheekScale = 1.0;
      t.rightCheekScale = 1.0;
      t.neckPitch = 0.0;
      t.neckYaw = 0.0;
      t.neckRoll = 0.0;
      t.headPitch = 0.0;
      t.headYaw = 0.0;
      t.headRoll = 0.0;
      this.targetPupilScale = 1.0;
      this.targetBlushOpacity = 0.0;
      this.setBrowAsymmetry(0.0, 0.0);
    }
  }

  update(dt) {
    const safeDt = Math.max(0.001, Math.min(0.05, dt));

    for (const [key, ch] of this.channels.entries()) {
      if (ch.elapsed < ch.duration) {
        ch.elapsed += safeDt;
        const progress = Math.min(1.0, ch.elapsed / ch.duration);
        const curve = easeOutBack(progress, 1.45);
        ch.current = ch.startVal + (ch.target - ch.startVal) * curve;
        if (progress >= 1.0) {
          ch.current = ch.target;
        }
      }
    }

    this.saccadeTimer += safeDt;
    if (this.saccadeTimer >= this.saccadeInterval) {
      this.saccadeTimer = 0.0;
      this.saccadeInterval = 1.8 + Math.random() * 2.2;
      this.microJitter.set(
        (Math.random() - 0.5) * 0.04,
        (Math.random() - 0.5) * 0.03
      );
    }

    const gazeTarget = this.targetPupilOffset.clone().add(this.microJitter);
    this.pupilOffset.lerp(gazeTarget, Math.min(1.0, safeDt * 22.0));
    this.pupilScale = THREE.MathUtils.damp(this.pupilScale, this.targetPupilScale, 10.0, safeDt);
    this.blushOpacity = THREE.MathUtils.damp(this.blushOpacity, this.targetBlushOpacity, 6.0, safeDt);

    const s = this.secondaryBoneState;
    const ts = this.targetSecondaryBoneState;
    s.jawPitch = THREE.MathUtils.damp(s.jawPitch, ts.jawPitch, 14.0, safeDt);
    s.jawForward = THREE.MathUtils.damp(s.jawForward, ts.jawForward, 12.0, safeDt);
    s.leftCheekScale = THREE.MathUtils.damp(s.leftCheekScale, ts.leftCheekScale, 10.0, safeDt);
    s.rightCheekScale = THREE.MathUtils.damp(s.rightCheekScale, ts.rightCheekScale, 10.0, safeDt);
    s.neckPitch = THREE.MathUtils.damp(s.neckPitch, ts.neckPitch, 8.0, safeDt);
    s.neckYaw = THREE.MathUtils.damp(s.neckYaw, ts.neckYaw, 8.0, safeDt);
    s.neckRoll = THREE.MathUtils.damp(s.neckRoll, ts.neckRoll, 8.0, safeDt);
    s.headPitch = THREE.MathUtils.damp(s.headPitch, ts.headPitch, 8.0, safeDt);
    s.headYaw = THREE.MathUtils.damp(s.headYaw, ts.headYaw, 8.0, safeDt);
    s.headRoll = THREE.MathUtils.damp(s.headRoll, ts.headRoll, 8.0, safeDt);
  }

  getMorphValue(name) {
    const ch = this.channels.get(name);
    return ch ? ch.current : 0.0;
  }

  getComputedMorphs() {
    const result = new Map();
    for (const [key, ch] of this.channels.entries()) {
      if (key.startsWith('viseme_')) continue;
      if (key.startsWith('custom_')) {
        const cleanKey = key.slice(7);
        result.set(cleanKey, Math.max(result.get(cleanKey) || 0.0, ch.current));
      } else {
        result.set(key, ch.current);
      }
    }

    for (const [vKey, val] of Object.entries(this.visemes)) {
      const vCh = this.channels.get(`viseme_${vKey}`);
      const curV = vCh ? vCh.current : val;
      if (curV > 0.001) {
        result.set(vKey, curV);
      }
    }

    if (this.blushOpacity > 0.01) {
      result.set('shy', Math.max(result.get('shy') || 0.0, this.blushOpacity));
      result.set('テレ', Math.max(result.get('テレ') || 0.0, this.blushOpacity));
      result.set('照れ', Math.max(result.get('照れ') || 0.0, this.blushOpacity));
    }

    return result;
  }

  getSecondaryBoneOffsets() {
    return {
      ...this.secondaryBoneState,
      pupilScale: this.pupilScale,
      pupilOffset: this.pupilOffset,
      blushOpacity: this.blushOpacity,
      browAsymmetry: this.browAsymmetry
    };
  }

  reset() {
    for (const ch of this.channels.values()) {
      ch.target = 0.0;
      ch.startVal = ch.current;
      ch.elapsed = 0.0;
      ch.duration = 0.25;
    }
    for (const k in this.visemes) {
      this.visemes[k] = 0.0;
    }
    this.targetSecondaryBoneState = {
      jawPitch: 0.0,
      jawForward: 0.0,
      leftCheekScale: 1.0,
      rightCheekScale: 1.0,
      tongueOut: 0.0,
      neckPitch: 0.0,
      neckYaw: 0.0,
      neckRoll: 0.0,
      headPitch: 0.0,
      headYaw: 0.0,
      headRoll: 0.0
    };
    this.targetPupilScale = 1.0;
    this.targetBlushOpacity = 0.0;
    this.setBrowAsymmetry(0.0, 0.0);
  }
}
