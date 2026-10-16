import * as THREE from 'three';

export class SquashAndStretchModifier {
    constructor() {
        this.vrm = null;
        this.enabled = false;
        this.volumeConservation = 1.0;
        this.exaggeration = 1.0;
        this.maxStretch = 1.35;
        this.minSquash = 0.75;
        this.stretchSpeed = 16.0;
        this.returnSpeed = 14.0;

        this.trackedBones = [];
        this.boneStates = new Map();
        this.previousPositions = new Map();
        this.velocities = new Map();
    }

    setVrm(vrm) {
        this.vrm = vrm;
        this.trackedBones = [];
        this.boneStates.clear();
        this.previousPositions.clear();
        this.velocities.clear();

        if (!vrm || !vrm.humanoid) return;

        const boneNames = [
            'spine', 'chest', 'upperChest'
        ];

        boneNames.forEach((name) => {
            const node = vrm.humanoid.getNormalizedBoneNode(name) || vrm.humanoid.getRawBoneNode(name);
            if (node) {
                this.trackedBones.push({ name, node });
                this.boneStates.set(node, {
                    currentScale: new THREE.Vector3(1, 1, 1),
                    targetScale: new THREE.Vector3(1, 1, 1),
                    arcOffset: new THREE.Vector3(0, 0, 0),
                    baseScale: node.scale.clone()
                });
                this.previousPositions.set(node, new THREE.Vector3());
                this.velocities.set(node, new THREE.Vector3());
            }
        });
    }

    applyImpulse(boneName, stretchFactor, duration = 0.15) {
        if (!this.vrm) return;
        const entry = this.trackedBones.find(b => b.name === boneName);
        if (!entry) return;

        const state = this.boneStates.get(entry.node);
        if (!state) return;

        const clampedStretch = Math.max(this.minSquash, Math.min(this.maxStretch, stretchFactor));
        const compensation = Math.pow(clampedStretch, -0.5 * this.exaggeration);

        state.targetScale.set(compensation, clampedStretch, compensation);
        this.enabled = true;
    }

    triggerSquash(intensity = 1.0) {
        const factor = Math.max(0.75, 1.0 - (0.2 * intensity));
        this.trackedBones.forEach(b => {
            if (b.name.includes('spine') || b.name.includes('chest')) {
                this.applyImpulse(b.name, factor);
            }
        });
    }

    triggerStretch(intensity = 1.0) {
        const factor = Math.min(1.25, 1.0 + (0.25 * intensity));
        this.trackedBones.forEach(b => {
            if (b.name.includes('spine') || b.name.includes('chest')) {
                this.applyImpulse(b.name, factor);
            }
        });
    }

    update(dt) {
        if (!this.enabled || !this.vrm || !this.vrm.scene) return;

        const safeDt = Math.max(0.001, Math.min(0.05, dt));
        let anyActive = false;

        for (let i = 0; i < this.trackedBones.length; i++) {
            const { name, node } = this.trackedBones[i];
            const state = this.boneStates.get(node);
            if (!state) continue;

            const diff = Math.abs(state.currentScale.y - state.targetScale.y);
            if (diff > 0.005 || state.targetScale.y !== 1.0) {
                anyActive = true;
                const blendSpeed = (state.targetScale.y > state.currentScale.y) ? this.stretchSpeed : this.returnSpeed;
                const factor = Math.min(1.0, safeDt * blendSpeed);
                state.currentScale.lerp(state.targetScale, factor);
                node.scale.copy(state.baseScale).multiply(state.currentScale);
                if (state.targetScale.y !== 1.0 && diff < 0.05) {
                    state.targetScale.set(1.0, 1.0, 1.0);
                }
            } else {
                node.scale.copy(state.baseScale);
            }
        }

        if (!anyActive) {
            this.enabled = false;
        }
    }
}
