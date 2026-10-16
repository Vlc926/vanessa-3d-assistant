import * as THREE from 'three';

export class FrameModulationController {
    constructor() {
        this.vrm = null;
        this.enabled = false;
        this.animeFps = 60.0;
        this.stepInterval = 1.0 / 60.0;
        this.accumulatedTime = 0.0;
        this.lastSampleTime = 0.0;

        this.sampledBoneRotations = new Map();
        this.targetBoneRotations = new Map();
        this.trackedBones = [];

        this.smearActive = false;
        this.smearVelocityThreshold = 3.6;
        this.smearIntensity = 0.0;
        this.onSmearTrigger = null;

        this.overshootPhase = 0.0;
        this.overshootActive = false;
        this.overshootDecay = 18.0;
        this.overshootFreq = 26.0;
        this.overshootAmplitude = 0.0;
    }

    setVrm(vrm) {
        this.vrm = vrm;
        this.trackedBones = [];
        this.sampledBoneRotations.clear();
        this.targetBoneRotations.clear();

        if (!vrm || !vrm.humanoid) return;

        const names = [
            'head', 'neck', 'spine', 'chest', 'upperChest'
        ];

        names.forEach(name => {
            const bone = vrm.humanoid.getNormalizedBoneNode(name) || vrm.humanoid.getRawBoneNode(name);
            if (bone) {
                this.trackedBones.push(bone);
                this.sampledBoneRotations.set(bone, bone.quaternion.clone());
                this.targetBoneRotations.set(bone, bone.quaternion.clone());
            }
        });
    }

    setAnimeFps(fps) {
        this.animeFps = Math.max(24.0, Math.min(60.0, Number(fps) || 60.0));
        this.stepInterval = 1.0 / this.animeFps;
    }

    triggerOvershoot(amplitude = 0.35) {
        this.overshootActive = true;
        this.overshootPhase = 0.0;
        this.overshootAmplitude = Math.max(0.1, Math.min(1.0, amplitude));
    }

    triggerSmear(intensity = 1.0) {
        this.smearActive = true;
        this.smearIntensity = Math.min(1.5, Math.max(0.2, intensity));
        if (this.onSmearTrigger) {
            this.onSmearTrigger(this.smearIntensity);
        }
    }

    update(dt) {
        if (!this.vrm || !this.vrm.humanoid) return;

        const safeDt = Math.max(0.001, Math.min(0.05, dt));
        this.accumulatedTime += safeDt;

        if (this.overshootActive) {
            this.overshootPhase += safeDt;
            const damp = Math.exp(-this.overshootDecay * this.overshootPhase);
            const wave = Math.cos(this.overshootFreq * this.overshootPhase);
            const currentOvershoot = this.overshootAmplitude * damp * wave;

            if (this.overshootPhase > 0.45 || damp < 0.02) {
                this.overshootActive = false;
                this.overshootAmplitude = 0.0;
            } else {
                const chest = this.vrm.humanoid.getNormalizedBoneNode('chest');
                if (chest) {
                    const qOffset = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), currentOvershoot * 0.05);
                    chest.quaternion.multiply(qOffset);
                }
            }
        }
    }
}
