import * as THREE from 'three';

export class AnimationEngine {
  constructor() {
    this.avatar = null;
    this.cognitiveState = 'IDLE';

    this.breathTime = 0.0;
    this.breathFreq = 0.25;

    this.idleTime = 0.0;
    this.blinkTimer = 3.0;
    this.isBlinking = false;
    this.blinkElapsed = 0.0;
    this.blinkDuration = 0.18;

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
    this.visemeWeights = { aa: 0.0, ih: 0.0, ou: 0.0, ee: 0.0, oh: 0.0 };

    this.perlinSeed = Math.random() * 100.0;
  }

  setAvatar(avatar) {
    this.avatar = avatar;
  }

  setDirective(directive) {
    if (!directive || typeof directive !== 'object') return;
    if (directive.state) {
      this.cognitiveState = String(directive.state).toUpperCase();
    }
    if (directive.emotion_vector) {
      for (const [k, v] of Object.entries(directive.emotion_vector)) {
        if (k in this.targetEmotion) {
          this.targetEmotion[k] = Math.max(0.0, Math.min(1.0, Number(v) || 0.0));
        }
      }
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
  }

  playGesture(name, duration = 3.0) {
    this.activeGesture = String(name || 'idle').toLowerCase();
    this.gestureDuration = Math.max(0.5, Number(duration) || 3.0);
    this.gestureTime = 0.0;
    this.gestureWeight = 0.0;
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

  _softNoise(t) {
    return Math.sin(t) * 0.5 + Math.sin(t * 2.3 + 1.2) * 0.3 + Math.sin(t * 4.7 + 2.8) * 0.2;
  }

  update(dt) {
    if (!this.avatar) return;
    const clampedDt = Math.min(0.045, dt);

    this._updateLayer4Expressions(clampedDt);
    this._updateLayer4LipSync(clampedDt);
    this._updateLayer0Idle(clampedDt);
    this._updateLayer1Cognitive(clampedDt);
    this._updateLayer2Gestures(clampedDt);
    this._updateLayer3LookAtIK(clampedDt);

    this.avatar.update(clampedDt);
  }

  _updateLayer0Idle(dt) {
    this.breathTime += dt * this.breathFreq * Math.PI * 2.0;
    this.idleTime += dt;

    const breath = Math.sin(this.breathTime);
    const breathCos = Math.cos(this.breathTime);

    const spine = this.avatar.getBone('spine');
    const chest = this.avatar.getBone('chest');
    const lShoulder = this.avatar.getBone('leftShoulder');
    const rShoulder = this.avatar.getBone('rightShoulder');
    const hips = this.avatar.getBone('hips');

    if (spine) {
      spine.rotation.x = THREE.MathUtils.damp(spine.rotation.x, breath * 0.022, 6.0, dt);
      spine.rotation.z = THREE.MathUtils.damp(spine.rotation.z, Math.sin(this.idleTime * 0.7) * 0.015, 4.0, dt);
    }
    if (chest) {
      chest.rotation.x = THREE.MathUtils.damp(chest.rotation.x, breath * 0.035, 6.0, dt);
    }
    if (lShoulder) {
      lShoulder.rotation.z = THREE.MathUtils.damp(lShoulder.rotation.z, -0.04 + breath * 0.015, 5.0, dt);
    }
    if (rShoulder) {
      rShoulder.rotation.z = THREE.MathUtils.damp(rShoulder.rotation.z, 0.04 - breath * 0.015, 5.0, dt);
    }
    if (hips) {
      const hipSway = Math.sin(this.idleTime * 0.85) * 0.020;
      hips.rotation.z = THREE.MathUtils.damp(hips.rotation.z, hipSway, 4.0, dt);
      hips.rotation.y = THREE.MathUtils.damp(hips.rotation.y, hipSway * 0.6, 4.0, dt);
    }

    this.blinkTimer -= dt;
    if (this.blinkTimer <= 0.0 && !this.isBlinking) {
      if (this.currentEmotion.joy < 0.70) {
        this.isBlinking = true;
        this.blinkElapsed = 0.0;
      } else {
        this.blinkTimer = 2.0 + Math.random() * 2.5;
      }
    }
    if (this.isBlinking) {
      this.blinkElapsed += dt;
      const progress = this.blinkElapsed / this.blinkDuration;
      let blinkVal = 0.0;
      if (progress <= 0.5) {
        blinkVal = progress / 0.5;
      } else if (progress <= 1.0) {
        blinkVal = 1.0 - ((progress - 0.5) / 0.5);
      } else {
        this.isBlinking = false;
        this.blinkTimer = 2.5 + Math.random() * 3.5;
        blinkVal = 0.0;
      }
      this.avatar.setExpression('blink', blinkVal);
    }
  }

  _updateLayer1Cognitive(dt) {
    const head = this.avatar.getBone('head');
    const neck = this.avatar.getBone('neck');
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
      const speechBob = Math.sin(this.idleTime * 4.2) * 0.035;
      targetHeadPitchX = speechBob;
      this.lookTarget.set(0.0, 0.0, 2.8);
    }

    if (spine && (this.cognitiveState === 'LISTENING' || this.cognitiveState === 'THINKING')) {
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
    if (progress <= 0.20) {
      this.gestureWeight = THREE.MathUtils.damp(this.gestureWeight, progress / 0.20, 10.0, dt);
    } else if (progress <= 0.80) {
      this.gestureWeight = 1.0;
    } else if (progress < 1.0) {
      this.gestureWeight = THREE.MathUtils.damp(this.gestureWeight, (1.0 - progress) / 0.20, 8.0, dt);
    } else {
      this.gestureWeight = 0.0;
      this.activeGesture = 'idle';
    }

    if (this.gestureWeight <= 0.001) return;
    const w = this.gestureWeight;

    const lArm = this.avatar.getBone('leftUpperArm');
    const rArm = this.avatar.getBone('rightUpperArm');
    const lForearm = this.avatar.getBone('leftLowerArm');
    const rForearm = this.avatar.getBone('rightLowerArm');

    if (this.activeGesture === 'explain_open_hands') {
      if (lArm) {
        lArm.rotation.x = THREE.MathUtils.damp(lArm.rotation.x, -0.35, 6.0, dt);
        lArm.rotation.z = THREE.MathUtils.damp(lArm.rotation.z, -0.65, 6.0, dt);
      }
      if (rArm) {
        rArm.rotation.x = THREE.MathUtils.damp(rArm.rotation.x, -0.35, 6.0, dt);
        rArm.rotation.z = THREE.MathUtils.damp(rArm.rotation.z, 0.65, 6.0, dt);
      }
      if (lForearm) {
        lForearm.rotation.x = THREE.MathUtils.damp(lForearm.rotation.x, 0.60, 6.0, dt);
      }
      if (rForearm) {
        rForearm.rotation.x = THREE.MathUtils.damp(rForearm.rotation.x, 0.60, 6.0, dt);
      }
    } else if (this.activeGesture === 'nod') {
      const head = this.avatar.getBone('head');
      if (head) {
        head.rotation.x = THREE.MathUtils.damp(head.rotation.x, Math.sin(this.gestureTime * 7.5) * 0.16 * w, 8.0, dt);
      }
    } else if (this.activeGesture === 'greet' || this.activeGesture === 'wave') {
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

  _updateLayer4LipSync(dt) {
    if (!this.isAudioPlaying || !this.analyser || !this.audioFreqData) {
      for (const v of ['aa', 'ih', 'ou', 'ee', 'oh']) {
        this.visemeWeights[v] = THREE.MathUtils.damp(this.visemeWeights[v], 0.0, 12.0, dt);
        this.avatar.setViseme(v, this.visemeWeights[v]);
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

    this.visemeWeights.aa = THREE.MathUtils.damp(this.visemeWeights.aa, energyAa * scale, 15.0, dt);
    this.visemeWeights.ee = THREE.MathUtils.damp(this.visemeWeights.ee, energyEe * scale, 15.0, dt);
    this.visemeWeights.ih = THREE.MathUtils.damp(this.visemeWeights.ih, energyIh * scale, 15.0, dt);
    this.visemeWeights.oh = THREE.MathUtils.damp(this.visemeWeights.oh, energyOh * scale, 15.0, dt);
    this.visemeWeights.ou = THREE.MathUtils.damp(this.visemeWeights.ou, energyOu * scale, 15.0, dt);

    this.avatar.setViseme('aa', this.visemeWeights.aa);
    this.avatar.setViseme('ee', this.visemeWeights.ee);
    this.avatar.setViseme('ih', this.visemeWeights.ih);
    this.avatar.setViseme('oh', this.visemeWeights.oh);
    this.avatar.setViseme('ou', this.visemeWeights.ou);
  }
}
