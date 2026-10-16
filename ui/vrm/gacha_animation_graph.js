import * as THREE from 'three';

export class GachaAnimationGraph {
    constructor() {
        this.vrm = null;
        this.modelStyle = 'zzz_urban';
        this.isLocomoting = false;
        this.locomotionSpeed = 1.0;
        this.walkCyclePhase = 0.0;
        this.pelvicYOffset = 0.0;
        this.pelvicRollOffset = 0.0;
        this.lookAheadYaw = 0.0;

        this.activeEmote = 'none';
        this.emoteProgress = 0.0;
        this.emoteDuration = 2.5;

        this.autoEmoteTimer = 0.0;
        this.nextAutoEmoteInterval = 6.0;

        this.baseHipsY = 0.0;
        this.hipsCaptured = false;
    }

    setVrm(vrm, modelKey = '') {
        this.vrm = vrm;
        this.hipsCaptured = false;
        const key = String(modelKey || '').toLowerCase();
        if (key.includes('vanessa')) {
            this.modelStyle = 'maid_refined';
        } else {
            this.modelStyle = 'zzz_urban';
        }

        if (vrm && vrm.humanoid) {
            const hips = vrm.humanoid.getNormalizedBoneNode('hips');
            if (hips) {
                this.baseHipsY = hips.position.y;
                this.hipsCaptured = true;
            }
        }
    }

    setModelStyle(style) {
        this.modelStyle = style === 'maid_refined' ? 'maid_refined' : 'zzz_urban';
    }

    setLocomotion(isLocomoting, speed = 1.0, targetYaw = 0.0, currentYaw = 0.0) {
        this.isLocomoting = Boolean(isLocomoting);
        this.locomotionSpeed = Math.max(0.1, Number(speed) || 1.0);
        let diff = targetYaw - currentYaw;
        while (diff > Math.PI) diff -= Math.PI * 2;
        while (diff < -Math.PI) diff += Math.PI * 2;
        this.lookAheadYaw = THREE.MathUtils.clamp(diff * 0.45, -0.4, 0.4);
    }

    handleConversationTurn(role, intent, emotion) {
        const intentClean = String(intent || '').toLowerCase();
        const emotionClean = String(emotion || '').toLowerCase();

        if (intentClean === 'question') {
            this.triggerEmote('thinking_chin', 3.2);
        } else if (emotionClean === 'happy' || emotionClean === 'joy') {
            this.triggerEmote('joyful_cheer', 2.8);
        } else if (emotionClean === 'surprised' || emotionClean === 'alert') {
            this.triggerEmote('alert_defense', 2.2);
        } else if (emotionClean === 'curious') {
            this.triggerEmote('curious_tilt', 3.0);
        } else {
            this.triggerEmote('confidence_hands', 2.6);
        }
    }

    triggerEmote(name, duration = 2.5) {
        this.activeEmote = name;
        this.emoteProgress = 0.0;
        this.emoteDuration = Math.max(0.5, duration);
        this.autoEmoteTimer = 0.0;
    }

    update(dt) {
        if (!this.vrm || !this.vrm.humanoid) return;

        this.updateLocomotion(dt);
        this.updateMaskedEmotes(dt);
    }

    updateLocomotion(dt) {
        const humanoid = this.vrm.humanoid;
        const hips = humanoid.getNormalizedBoneNode('hips');
        const spine = humanoid.getNormalizedBoneNode('spine');
        const head = humanoid.getNormalizedBoneNode('head');
        const lArm = humanoid.getNormalizedBoneNode('leftUpperArm');
        const rArm = humanoid.getNormalizedBoneNode('rightUpperArm');

        if (!hips) return;
        if (!this.hipsCaptured) {
            this.baseHipsY = hips.position.y;
            this.hipsCaptured = true;
        }

        if (this.isLocomoting) {
            const cycleSpeed = (this.modelStyle === 'zzz_urban' ? 5.8 : 4.2) * Math.min(1.4, this.locomotionSpeed);
            this.walkCyclePhase = (this.walkCyclePhase + dt * cycleSpeed) % (Math.PI * 2);

            const bobAmp = this.modelStyle === 'zzz_urban' ? 0.024 : 0.012;
            this.pelvicYOffset = -Math.abs(Math.sin(this.walkCyclePhase)) * bobAmp;
            hips.position.y = this.baseHipsY + this.pelvicYOffset;

            const rollAmp = this.modelStyle === 'zzz_urban' ? 0.045 : 0.022;
            this.pelvicRollOffset = Math.sin(this.walkCyclePhase) * rollAmp;
            const qPelvisRoll = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), this.pelvicRollOffset);
            hips.quaternion.slerp(qPelvisRoll, 0.18);

            if (spine) {
                const qSpineCounter = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), -this.pelvicRollOffset * 0.65);
                spine.quaternion.slerp(qSpineCounter, 0.15);
            }

            if (head && Math.abs(this.lookAheadYaw) > 0.01) {
                const qHeadYaw = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), this.lookAheadYaw);
                head.quaternion.slerp(qHeadYaw, 0.15);
            }

            if (this.activeEmote === 'none' && lArm && rArm) {
                const swingAmp = this.modelStyle === 'zzz_urban' ? 0.38 : 0.16;
                const swingL = Math.sin(this.walkCyclePhase) * swingAmp;
                const swingR = -Math.sin(this.walkCyclePhase) * swingAmp;

                const qSwingL = new THREE.Quaternion().setFromEuler(new THREE.Euler(swingL, 0, -0.65, 'ZXY'));
                const qSwingR = new THREE.Quaternion().setFromEuler(new THREE.Euler(swingR, 0, 0.65, 'ZXY'));
                lArm.quaternion.slerp(qSwingL, 0.22);
                rArm.quaternion.slerp(qSwingR, 0.22);
            }
        } else {
            hips.position.y += (this.baseHipsY - hips.position.y) * Math.min(1.0, dt * 8.0);
        }
    }

    updateMaskedEmotes(dt) {
        if (this.activeEmote === 'none') {
            this.autoEmoteTimer += dt;
            if (this.autoEmoteTimer >= this.nextAutoEmoteInterval) {
                this.autoEmoteTimer = 0.0;
                this.nextAutoEmoteInterval = 7.0 + Math.random() * 8.0;
                const candidates = ['confidence_hands', 'curious_tilt', 'thinking_chin', 'chibi_cute_paws'];
                const choice = candidates[Math.floor(Math.random() * candidates.length)];
                this.triggerEmote(choice, 2.8);
            }
            return;
        }

        this.emoteProgress += dt / this.emoteDuration;
        const curve = Math.sin(Math.min(Math.PI, this.emoteProgress * Math.PI));

        const humanoid = this.vrm.humanoid;
        if (!humanoid) return;

        const spine = humanoid.getNormalizedBoneNode('spine');
        const head = humanoid.getNormalizedBoneNode('head');
        const lArm = humanoid.getNormalizedBoneNode('leftUpperArm');
        const rArm = humanoid.getNormalizedBoneNode('rightUpperArm');
        const lForearm = humanoid.getNormalizedBoneNode('leftLowerArm');
        const rForearm = humanoid.getNormalizedBoneNode('rightLowerArm');

        if (this.activeEmote === 'thinking_chin') {
            if (head) {
                const qH = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.04, -0.06, 0.08, 'YXZ'));
                head.quaternion.slerp(qH, 0.15 * curve);
            }
            if (rArm && rForearm) {
                const qRA = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.28, 0, 0.25, 'ZXY'));
                const qRF = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -0.65);
                rArm.quaternion.slerp(qRA, 0.18 * curve);
                rForearm.quaternion.slerp(qRF, 0.18 * curve);
            }
        } else if (this.activeEmote === 'chibi_cute_paws' || this.activeEmote === 'joyful_cheer') {
            if (head) {
                const qH = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.04, 0.05, 0.05, 'YXZ'));
                head.quaternion.slerp(qH, 0.18 * curve);
            }
            if (spine) {
                const qS = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.04, 0, 0.02, 'YXZ'));
                spine.quaternion.slerp(qS, 0.12 * curve);
            }
            if (lArm && rArm && lForearm && rForearm) {
                const qLA = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.25, 0.1, -0.28, 'ZXY'));
                const qRA = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.25, -0.1, 0.28, 'ZXY'));
                const qLF = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), 0.85);
                const qRF = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -0.85);
                lArm.quaternion.slerp(qLA, 0.22 * curve);
                rArm.quaternion.slerp(qRA, 0.22 * curve);
                lForearm.quaternion.slerp(qLF, 0.22 * curve);
                rForearm.quaternion.slerp(qRF, 0.22 * curve);
            }
        } else if (this.activeEmote === 'curious_tilt') {
            if (head) {
                const qH = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.05, 0.10, 0.10, 'YXZ'));
                head.quaternion.slerp(qH, 0.15 * curve);
            }
            if (spine) {
                const qS = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.03, 0, 0.02, 'YXZ'));
                spine.quaternion.slerp(qS, 0.10 * curve);
            }
        } else if (this.activeEmote === 'confidence_hands') {
            if (lArm && rArm && lForearm && rForearm) {
                const qLA = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.12, 0, -0.35, 'ZXY'));
                const qRA = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.12, 0, 0.35, 'ZXY'));
                const qLF = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), 0.35);
                const qRF = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -0.35);
                lArm.quaternion.slerp(qLA, 0.18 * curve);
                rArm.quaternion.slerp(qRA, 0.18 * curve);
                lForearm.quaternion.slerp(qLF, 0.18 * curve);
                rForearm.quaternion.slerp(qRF, 0.18 * curve);
            }
        } else if (this.activeEmote === 'alert_defense') {
            if (spine) {
                const qS = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.06, 0, 0, 'YXZ'));
                spine.quaternion.slerp(qS, 0.12 * curve);
            }
            if (lArm && rArm) {
                const qLA = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.25, 0, -0.30, 'ZXY'));
                const qRA = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.25, 0, 0.30, 'ZXY'));
                lArm.quaternion.slerp(qLA, 0.18 * curve);
                rArm.quaternion.slerp(qRA, 0.18 * curve);
            }
        }

        if (this.emoteProgress >= 1.0) {
            this.activeEmote = 'none';
        }
    }
}
