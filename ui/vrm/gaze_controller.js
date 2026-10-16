import * as THREE from 'three';
import { VRMExpressionPresetName } from '@pixiv/three-vrm';

export class GazeController {
    constructor(scene) {
        this.scene = scene;
        this.targetLookPos = new THREE.Vector3(0, 1.35, 2.0);
        this.currentLookPos = new THREE.Vector3(0, 1.35, 2.0);
        this.lookVelocity = new THREE.Vector3(0, 0, 0);

        this.lookTargetObj = new THREE.Object3D();
        this.lookTargetObj.position.copy(this.currentLookPos);
        if (this.scene) this.scene.add(this.lookTargetObj);

        this.saccadeOffset = new THREE.Vector3(0, 0, 0);
        this.saccadeTimer = 1.8 + Math.random() * 1.4;
        this.driftPhase = 0.0;

        this.blinkTimer = 0.0;
        this.blinkInterval = 3.5;
        this.blinkProgress = 0.0;
        this.isBlinking = false;
        this.lastLookTime = performance.now();

        this.maxNeckYaw = 0.61;
        this.maxHeadYaw = 0.785;
        this.minPitch = -0.43;
        this.maxPitch = 0.52;
    }

    lookAt(x, y, salience = 1.0) {
        this.lastLookTime = performance.now();
        const weight = Math.max(0.2, Math.min(1.5, Number(salience) || 1.0));
        const clampedX = Math.max(-1.1, Math.min(1.1, (Number(x) || 0.0) * 1.1 * weight));
        const clampedY = Math.max(-0.45, Math.min(0.45, Number(y) || 0.0));
        this.targetLookPos.set(clampedX, 1.35 + clampedY * 0.35, 2.0);
    }

    update(dt, vrm) {
        if (!vrm) return;
        const now = performance.now();
        if (now - this.lastLookTime > 4500) {
            this.targetLookPos.set(0, 1.35, 2.0);
        }

        this.saccadeTimer -= dt;
        if (this.saccadeTimer <= 0) {
            this.saccadeTimer = 1.8 + Math.random() * 1.4;
            this.saccadeOffset.set(
                (Math.random() - 0.5) * 0.12,
                (Math.random() - 0.5) * 0.08,
                0
            );
        }

        this.driftPhase += dt * 1.5;
        const driftX = Math.sin(this.driftPhase) * 0.02;
        const driftY = Math.cos(this.driftPhase * 0.8) * 0.015;

        const effectiveTarget = this.targetLookPos.clone().add(this.saccadeOffset).add(new THREE.Vector3(driftX, driftY, 0));

        const omega = 8.5;
        const f = 1.0 + omega * dt;
        const oo = omega * omega;
        const hoo = dt * oo;
        const hhoo = dt * hoo;
        const detInv = 1.0 / (f + hhoo);
        const diff = this.currentLookPos.clone().sub(effectiveTarget);
        this.currentLookPos.copy(diff.multiplyScalar(f).add(this.lookVelocity.clone().multiplyScalar(dt)).multiplyScalar(detInv)).add(effectiveTarget);
        this.lookVelocity.copy(this.lookVelocity.clone().sub(diff.multiplyScalar(hoo)).multiplyScalar(detInv));

        this.lookTargetObj.position.copy(this.currentLookPos);

        if (vrm.lookAt) {
            vrm.lookAt.target = this.lookTargetObj;
            vrm.lookAt.autoUpdate = true;
        }

        this.updateBlink(dt, vrm);
    }

    updateBlink(dt, vrm) {
        this.blinkTimer += dt;
        if (!this.isBlinking && this.blinkTimer >= this.blinkInterval) {
            this.isBlinking = true;
            this.blinkProgress = 0;
        }
        if (this.isBlinking) {
            this.blinkProgress += dt * 7.5;
            let weight = 0;
            if (this.blinkProgress <= 1.0) {
                weight = Math.sin(this.blinkProgress * Math.PI);
            } else {
                this.isBlinking = false;
                this.blinkTimer = 0;
                this.blinkInterval = 2.5 + Math.random() * 3.0;
                weight = 0;
            }
            const clampedW = Math.max(0, Math.min(1, weight));
            if (vrm.expressionManager) {
                try {
                    vrm.expressionManager.setValue(VRMExpressionPresetName.Blink, clampedW);
                } catch (e) {}
            }
        }
    }
}
