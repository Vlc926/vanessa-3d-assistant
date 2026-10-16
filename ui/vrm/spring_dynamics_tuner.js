import * as THREE from 'three';

const _vInertia = new THREE.Vector3();
const _vWind = new THREE.Vector3();
const _vEffGrav = new THREE.Vector3();
const _vPos = new THREE.Vector3();
const _vDelta = new THREE.Vector3();

export class SpringDynamicsTuner {
    constructor() {
        this.vrm = null;
        this.enabled = true;
        this.profile = 'dynamic';
        this.cachedJoints = [];

        this.stiffnessMultiplier = 1.0;
        this.dragMultiplier = 1.0;
        this.gravityMultiplier = 1.0;

        this.prevRootPos = new THREE.Vector3();
        this.rootVel = new THREE.Vector3();
        this.rootAccel = new THREE.Vector3();
        this.externalImpulse = new THREE.Vector3();

        this.windTime = 0.0;
        this.windStrength = 0.035;
        this.breathTime = 0.0;
        this.initialized = false;
    }

    setVrm(vrm) {
        this.vrm = vrm;
        this.cachedJoints = [];
        this.initialized = false;
        if (!vrm) return;

        this.initSpringJoints();
    }

    initSpringJoints() {
        if (!this.vrm || !this.vrm.springBoneManager) return;

        const manager = this.vrm.springBoneManager;
        const joints = manager.joints || [];
        this.cachedJoints = [];

        joints.forEach(joint => {
            if (!joint || !joint.settings) return;
            if (joint._baseStiffness === undefined) {
                joint._baseStiffness = typeof joint.settings.stiffness === 'number' ? joint.settings.stiffness : 0.8;
                joint._baseDrag = typeof joint.settings.dragForce === 'number' ? joint.settings.dragForce : 0.5;
                joint._baseGravityPower = typeof joint.settings.gravityPower === 'number' ? joint.settings.gravityPower : 0.0;
                joint._baseGravityDir = joint.settings.gravityDir ? joint.settings.gravityDir.clone() : new THREE.Vector3(0, -1, 0);
                joint._baseHitRadius = typeof joint.settings.hitRadius === 'number' ? joint.settings.hitRadius : 0.02;
            }
            this.cachedJoints.push(joint);
        });

        if (this.vrm.humanoid) {
            const hips = this.vrm.humanoid.getNormalizedBoneNode('hips');
            if (hips) {
                hips.getWorldPosition(this.prevRootPos);
                this.initialized = true;
            }
        }

        this.applyProfileMultipliers();
    }

    setProfile(profile) {
        this.profile = profile || 'dynamic';
        this.applyProfileMultipliers();
    }

    applyProfileMultipliers() {
        if (this.profile === 'snappy') {
            this.stiffnessMultiplier = 1.25;
            this.dragMultiplier = 1.15;
            this.gravityMultiplier = 1.0;
            this.windStrength = 0.025;
        } else if (this.profile === 'soft') {
            this.stiffnessMultiplier = 0.75;
            this.dragMultiplier = 0.85;
            this.gravityMultiplier = 0.9;
            this.windStrength = 0.055;
        } else if (this.profile === 'breezy') {
            this.stiffnessMultiplier = 0.90;
            this.dragMultiplier = 0.80;
            this.gravityMultiplier = 1.0;
            this.windStrength = 0.085;
        } else if (this.profile === 'tactical') {
            this.stiffnessMultiplier = 1.35;
            this.dragMultiplier = 1.30;
            this.gravityMultiplier = 1.1;
            this.windStrength = 0.015;
        } else {
            this.stiffnessMultiplier = 1.0;
            this.dragMultiplier = 1.0;
            this.gravityMultiplier = 1.0;
            this.windStrength = 0.04;
        }
    }

    applyExternalImpulse(dx, dy, dt) {
        const safeDt = Math.max(0.001, Math.min(0.05, Number(dt) || 0.016));
        const invDt = 1.0 / safeDt;
        const impulseX = -Number(dx || 0.0) * invDt * 0.0003;
        const impulseY = -Number(dy || 0.0) * invDt * 0.0003;
        this.externalImpulse.x = THREE.MathUtils.clamp(this.externalImpulse.x + impulseX, -0.6, 0.6);
        this.externalImpulse.y = THREE.MathUtils.clamp(this.externalImpulse.y + impulseY, -0.6, 0.6);
    }

    update(dt) {
        if (!this.enabled || !this.vrm) return;
        if (this.cachedJoints.length === 0) {
            this.initSpringJoints();
            if (this.cachedJoints.length === 0) return;
        }

        const safeDt = Math.max(0.001, Math.min(0.05, Number(dt) || 0.016));

        if (this.vrm.humanoid) {
            const hips = this.vrm.humanoid.getNormalizedBoneNode('hips');
            if (hips) {
                hips.getWorldPosition(_vPos);
                if (this.initialized) {
                    _vDelta.copy(_vPos).sub(this.prevRootPos);
                    const instantVel = _vDelta.divideScalar(safeDt);
                    const instantAccel = instantVel.clone().sub(this.rootVel).divideScalar(safeDt);

                    this.rootVel.lerp(instantVel, Math.min(1.0, safeDt * 10.0));
                    this.rootAccel.lerp(instantAccel, Math.min(1.0, safeDt * 8.0));
                }
                this.prevRootPos.copy(_vPos);
                this.initialized = true;
            }
        }

        this.externalImpulse.lerp(THREE.Vector3.prototype, Math.min(1.0, safeDt * 5.0));

        this.windTime += safeDt * 1.6;
        _vWind.set(
            Math.sin(this.windTime * 1.3) * this.windStrength + Math.sin(this.windTime * 2.7) * (this.windStrength * 0.4),
            Math.sin(this.windTime * 0.8) * (this.windStrength * 0.2),
            Math.cos(this.windTime * 1.1) * (this.windStrength * 0.7)
        );

        _vInertia.set(
            -this.rootAccel.x * 0.04 + this.externalImpulse.x,
            -this.rootAccel.y * 0.04 + this.externalImpulse.y,
            -this.rootAccel.z * 0.04
        );
        _vInertia.clampScalar(-0.45, 0.45);

        this.breathTime += safeDt * 2.2;
        const breathPulse = Math.sin(this.breathTime) * 0.015;

        const moveSpeed = this.rootVel.length();
        const dynamicDragBonus = THREE.MathUtils.clamp(moveSpeed * 0.08, 0.0, 0.35);

        const totalJoints = this.cachedJoints.length;
        for (let i = 0; i < totalJoints; i++) {
            const joint = this.cachedJoints[i];
            const settings = joint.settings;
            if (!settings) continue;

            const baseStiff = joint._baseStiffness;
            const baseDrag = joint._baseDrag;
            const baseGravPower = joint._baseGravityPower;
            const baseGravDir = joint._baseGravityDir;

            settings.stiffness = THREE.MathUtils.clamp(baseStiff * this.stiffnessMultiplier, 0.08, 2.2);
            settings.dragForce = THREE.MathUtils.clamp(baseDrag * this.dragMultiplier + dynamicDragBonus, 0.35, 0.92);
            settings.gravityPower = Math.max(0.0, baseGravPower * this.gravityMultiplier + breathPulse);

            _vEffGrav.copy(baseGravDir).add(_vInertia).add(_vWind);
            if (_vEffGrav.lengthSq() > 0.0001) {
                _vEffGrav.normalize();
            } else {
                _vEffGrav.set(0, -1, 0);
            }

            if (settings.gravityDir) {
                settings.gravityDir.copy(_vEffGrav);
            }
        }
    }
}
