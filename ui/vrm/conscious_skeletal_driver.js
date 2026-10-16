import * as THREE from 'three';

const _qHipTarget = new THREE.Quaternion();
const _qSpineTarget = new THREE.Quaternion();
const _qChestTarget = new THREE.Quaternion();
const _qUpperChestTarget = new THREE.Quaternion();
const _qNeckTarget = new THREE.Quaternion();
const _qHeadTarget = new THREE.Quaternion();
const _qShoulderL = new THREE.Quaternion();
const _qShoulderR = new THREE.Quaternion();
const _qHandL = new THREE.Quaternion();
const _qHandR = new THREE.Quaternion();
const _qArmL = new THREE.Quaternion();
const _qArmR = new THREE.Quaternion();
const _qElbowL = new THREE.Quaternion();
const _qElbowR = new THREE.Quaternion();
const _qLegL = new THREE.Quaternion();
const _qLegR = new THREE.Quaternion();

const _eRot = new THREE.Euler();
const _vAxisX = new THREE.Vector3(1, 0, 0);
const _vAxisY = new THREE.Vector3(0, 1, 0);

export class ConsciousSkeletalDriver {
    constructor() {
        this.vrm = null;
        this.packet = null;

        this.targetHeadTilt = new THREE.Vector3(0, 0, 0);
        this.currentHeadTilt = new THREE.Vector3(0, 0, 0);

        this.targetSpineLean = new THREE.Vector3(0, 0, 0);
        this.currentSpineLean = new THREE.Vector3(0, 0, 0);

        this.contrappostoShift = 0.0;
        this.contrappostoCurrent = 0.0;

        this.rhythmPhase = 0.0;
        this.tempoBpm = 120.0;
        this.swayEnabled = false;

        this.inertiaLean = new THREE.Vector2(0, 0);
        this.currentInertia = new THREE.Vector2(0, 0);
        this.squashFactor = 1.0;
        this.currentSquash = 1.0;

        this.armRelaxation = 0.85;
        this.kneeFlexion = 0.04;

        this.dualIdleMode = 'active_dialogue';
        this.pcIdleSec = 0.0;
        this.vanessaIdleSec = 0.0;

        this.tacticalActive = false;
        this.isLocomoting = false;
        this.breathPhase = 0.0;
    }

    setVrm(vrm) {
        this.vrm = vrm;
    }

    applyPacket(packet) {
        if (!packet) return;
        this.packet = packet;

        if (packet.channel3_media) {
            this.swayEnabled = Boolean(packet.channel3_media.sway_enabled);
            this.tempoBpm = Number(packet.channel3_media.tempo_bpm) || 120.0;
        }

        if (packet.channel4_haptics) {
            const h = packet.channel4_haptics;
            if (h.inertia_lean && Array.isArray(h.inertia_lean)) {
                this.inertiaLean.set(h.inertia_lean[0] || 0.0, h.inertia_lean[1] || 0.0);
            }
            this.squashFactor = Number(h.squash_factor) || 1.0;
        }

        if (packet.channel5_dual_idle) {
            const d = packet.channel5_dual_idle;
            this.pcIdleSec = Number(d.pc_idle_seconds) || 0.0;
            this.vanessaIdleSec = Number(d.vanessa_idle_seconds) || 0.0;
            this.dualIdleMode = String(d.mode || 'active_dialogue');
        }

        if (packet.channel6_tactical) {
            this.tacticalActive = Boolean(packet.channel6_tactical.active);
        } else {
            this.tacticalActive = false;
        }

        if (packet.isLocomoting !== undefined) {
            this.isLocomoting = Boolean(packet.isLocomoting);
        }

        if (packet.biomechanical_pose) {
            const p = packet.biomechanical_pose;
            if (p.head_tilt && Array.isArray(p.head_tilt)) {
                this.targetHeadTilt.set(p.head_tilt[0] || 0, p.head_tilt[1] || 0, p.head_tilt[2] || 0);
            }
            if (p.spine_lean && Array.isArray(p.spine_lean)) {
                this.targetSpineLean.set(p.spine_lean[0] || 0, p.spine_lean[1] || 0, p.spine_lean[2] || 0);
            }
            this.contrappostoShift = Number(p.contrapposto_shift) || 0.0;
            this.armRelaxation = Number(p.arm_relaxation) || 0.85;
            this.kneeFlexion = Number(p.knee_flexion) || 0.04;
        }
    }

    update(dt) {
        if (!this.vrm || !this.vrm.humanoid) return;

        const lerpFactor = Math.min(1.0, dt * 5.5);
        this.currentHeadTilt.lerp(this.targetHeadTilt, lerpFactor);
        this.currentSpineLean.lerp(this.targetSpineLean, lerpFactor);
        this.contrappostoCurrent += (this.contrappostoShift - this.contrappostoCurrent) * lerpFactor;
        this.currentInertia.lerp(this.inertiaLean, lerpFactor * 1.5);
        this.currentSquash += (this.squashFactor - this.currentSquash) * (lerpFactor * 2.0);

        this.breathPhase += dt * (this.dualIdleMode === 'system_sleep' ? 1.2 : 2.2);
        const breathSine = Math.sin(this.breathPhase);

        if (this.swayEnabled) {
            const bps = this.tempoBpm / 60.0;
            this.rhythmPhase = (this.rhythmPhase + dt * bps * 2.0 * Math.PI) % (2.0 * Math.PI);
        }

        const musicSwayX = this.swayEnabled ? Math.sin(this.rhythmPhase) * 0.03 : 0.0;
        const musicSwayY = this.swayEnabled ? Math.cos(this.rhythmPhase * 0.5) * 0.025 : 0.0;

        const humanoid = this.vrm.humanoid;
        const hips = humanoid.getNormalizedBoneNode('hips');
        const spine = humanoid.getNormalizedBoneNode('spine');
        const chest = humanoid.getNormalizedBoneNode('chest');
        const upperChest = humanoid.getNormalizedBoneNode('upperChest');
        const neck = humanoid.getNormalizedBoneNode('neck');
        const head = humanoid.getNormalizedBoneNode('head');

        const leftShoulder = humanoid.getNormalizedBoneNode('leftShoulder');
        const rightShoulder = humanoid.getNormalizedBoneNode('rightShoulder');
        const leftUpperArm = humanoid.getNormalizedBoneNode('leftUpperArm');
        const rightUpperArm = humanoid.getNormalizedBoneNode('rightUpperArm');
        const leftLowerArm = humanoid.getNormalizedBoneNode('leftLowerArm');
        const rightLowerArm = humanoid.getNormalizedBoneNode('rightLowerArm');
        const leftHand = humanoid.getNormalizedBoneNode('leftHand');
        const rightHand = humanoid.getNormalizedBoneNode('rightHand');

        const leftUpperLeg = humanoid.getNormalizedBoneNode('leftUpperLeg');
        const rightUpperLeg = humanoid.getNormalizedBoneNode('rightUpperLeg');

        if (hips) {
            if (this.swayEnabled) {
                const hipTiltZ = THREE.MathUtils.clamp(this.contrappostoCurrent * 0.02 + musicSwayY * 0.5, -0.05, 0.05);
                _eRot.set(0, 0, hipTiltZ, 'YXZ');
                _qHipTarget.setFromEuler(_eRot);
                hips.quaternion.slerp(_qHipTarget, 0.05);
            }

            if (Math.abs(this.currentSquash - 1.0) > 0.005) {
                hips.scale.set(
                    1.0 / Math.sqrt(this.currentSquash),
                    this.currentSquash,
                    1.0 / Math.sqrt(this.currentSquash)
                );
            }
        }

        if (spine && (Math.abs(this.currentSpineLean.x) > 0.001 || this.swayEnabled)) {
            const spinePitch = THREE.MathUtils.clamp(breathSine * 0.008 - this.currentInertia.y * 0.05, -0.06, 0.06);
            const spineRoll = THREE.MathUtils.clamp(-this.contrappostoCurrent * 0.015 + musicSwayY * 0.25, -0.05, 0.05);
            _eRot.set(spinePitch, 0, spineRoll, 'YXZ');
            _qSpineTarget.setFromEuler(_eRot);
            spine.quaternion.slerp(_qSpineTarget, 0.10);
        }

        if (chest && (Math.abs(this.currentSpineLean.x) > 0.001 || this.swayEnabled)) {
            const factor = upperChest ? 0.55 : 1.0;
            const chestBreath = THREE.MathUtils.clamp(breathSine * 0.012 * factor, -0.02, 0.02);
            _qChestTarget.setFromAxisAngle(_vAxisX, chestBreath);
            chest.quaternion.slerp(_qChestTarget, 0.08);
        }

        if (upperChest && (Math.abs(this.currentSpineLean.x) > 0.001 || this.swayEnabled)) {
            const upperBreath = THREE.MathUtils.clamp(breathSine * 0.010 * 0.45, -0.015, 0.015);
            _qUpperChestTarget.setFromAxisAngle(_vAxisX, upperBreath);
            upperChest.quaternion.slerp(_qUpperChestTarget, 0.08);
        }

        if (leftShoulder && rightShoulder) {
            const shoulderLift = THREE.MathUtils.clamp(breathSine * 0.006, -0.01, 0.01);
            _eRot.set(0, 0, shoulderLift, 'YXZ');
            _qShoulderL.setFromEuler(_eRot);
            _eRot.set(0, 0, -shoulderLift, 'YXZ');
            _qShoulderR.setFromEuler(_eRot);
            leftShoulder.quaternion.slerp(_qShoulderL, 0.08);
            rightShoulder.quaternion.slerp(_qShoulderR, 0.08);
        }

        if (neck && (this.currentHeadTilt.lengthSq() > 0.0001 || this.swayEnabled)) {
            const neckPitch = THREE.MathUtils.clamp(this.currentHeadTilt.x * 0.25, -0.15, 0.15);
            const neckYaw = THREE.MathUtils.clamp(this.currentHeadTilt.y * 0.25 + musicSwayX * 0.3, -0.18, 0.18);
            const neckRoll = THREE.MathUtils.clamp(this.currentHeadTilt.z * 0.2, -0.10, 0.10);
            _eRot.set(neckPitch, neckYaw, neckRoll, 'YXZ');
            _qNeckTarget.setFromEuler(_eRot);
            neck.quaternion.slerp(_qNeckTarget, 0.12);
        }

        if (head && (this.currentHeadTilt.lengthSq() > 0.0001 || this.swayEnabled)) {
            const headPitch = THREE.MathUtils.clamp(this.currentHeadTilt.x * 0.35, -0.20, 0.20);
            const headYaw = THREE.MathUtils.clamp(this.currentHeadTilt.y * 0.35 + musicSwayX * 0.5, -0.25, 0.25);
            const headRoll = THREE.MathUtils.clamp(this.currentHeadTilt.z * 0.35, -0.15, 0.15);
            _eRot.set(headPitch, headYaw, headRoll, 'YXZ');
            _qHeadTarget.setFromEuler(_eRot);
            head.quaternion.slerp(_qHeadTarget, 0.15);
        }

        if (!this.tacticalActive && !this.isLocomoting && leftHand && rightHand) {
            _eRot.set(0.04, 0.02, -0.06, 'XYZ');
            _qHandL.setFromEuler(_eRot);
            _eRot.set(0.04, -0.02, 0.06, 'XYZ');
            _qHandR.setFromEuler(_eRot);
            leftHand.quaternion.slerp(_qHandL, 0.05);
            rightHand.quaternion.slerp(_qHandR, 0.05);
        }

        if (this.tacticalActive) {
            if (leftUpperArm && rightUpperArm) {
                _eRot.set(0.35, 0, -0.35, 'ZXY');
                _qArmL.setFromEuler(_eRot);
                _eRot.set(0.35, 0, 0.35, 'ZXY');
                _qArmR.setFromEuler(_eRot);
                leftUpperArm.quaternion.slerp(_qArmL, 0.15);
                rightUpperArm.quaternion.slerp(_qArmR, 0.15);
            }
            if (leftLowerArm && rightLowerArm) {
                _qElbowL.setFromAxisAngle(_vAxisY, 0.65);
                _qElbowR.setFromAxisAngle(_vAxisY, -0.65);
                leftLowerArm.quaternion.slerp(_qElbowL, 0.15);
                rightLowerArm.quaternion.slerp(_qElbowR, 0.15);
            }
            if (!this.isLocomoting && leftUpperLeg && rightUpperLeg) {
                _eRot.set(0.08, 0, -0.05, 'YXZ');
                _qLegL.setFromEuler(_eRot);
                _eRot.set(0.08, 0, 0.05, 'YXZ');
                _qLegR.setFromEuler(_eRot);
                leftUpperLeg.quaternion.slerp(_qLegL, 0.15);
                rightUpperLeg.quaternion.slerp(_qLegR, 0.15);
            }
        }
    }
}
