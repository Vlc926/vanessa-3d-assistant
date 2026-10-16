import * as THREE from 'three';

export class GachaCinematicController {
    constructor() {
        this.vrm = null;
        this.enabled = true;
        this.cinematicTime = 0.0;
        this.stepTimer = 0.0;
        this.stepInterval = 1.0 / 24.0;

        this.weightShiftPhase = 0.0;
        this.weightShiftDuration = 12.0;
        this.activeStanceLeg = 'left';

        this.blinkTimer = 0.0;
        this.nextBlinkInterval = 3.5;
        this.isBlinking = false;
        this.blinkProgress = 0.0;

        this.fidgetTimer = 0.0;
        this.nextFidgetInterval = 8.0;
        this.activeFidget = 'none';
        this.fidgetProgress = 0.0;

        this.combatStance = false;
        this.combatBlend = 0.0;

        this.inertiaMomentum = new THREE.Vector3(0, 0, 0);
        this.prevHipsPos = new THREE.Vector3(0, 0, 0);

        this.springStiffnessMultiplier = 1.0;
        this.springDragMultiplier = 1.0;
    }

    setVrm(vrm) {
        this.vrm = vrm;
        if (vrm && vrm.humanoid) {
            const hips = vrm.humanoid.getNormalizedBoneNode('hips');
            if (hips) {
                hips.getWorldPosition(this.prevHipsPos);
            }
        }
    }

    setCombatStance(active) {
        this.combatStance = Boolean(active);
    }

    triggerFidget(name) {
        this.activeFidget = name || 'confidence_pose';
        this.fidgetProgress = 0.0;
        this.fidgetTimer = 0.0;
    }

    update(dt) {
        if (!this.vrm || !this.enabled) return;

        this.cinematicTime += dt;
        this.stepTimer += dt;
        if (this.stepTimer < this.stepInterval) {
            return;
        }
        const steppedDt = this.stepTimer;
        this.stepTimer = 0.0;

        this.updateLivingBase(steppedDt);
        this.updateMicroBlinks(steppedDt);
        this.updateAttitudeFidgets(steppedDt);
        this.updateCombatLayer(steppedDt);
        this.updateSecondarySprings(steppedDt);
    }

    updateLivingBase(dt) {
        this.weightShiftPhase += dt;
        if (this.weightShiftPhase >= this.weightShiftDuration) {
            this.weightShiftPhase = 0.0;
            this.activeStanceLeg = (this.activeStanceLeg === 'left') ? 'right' : 'left';
            this.weightShiftDuration = 10.0 + Math.random() * 8.0;
        }

        const t = this.weightShiftPhase / this.weightShiftDuration;
        const smoothShift = Math.sin(t * Math.PI);
        const shiftSign = (this.activeStanceLeg === 'left') ? 1.0 : -1.0;
        const pelvicTilt = shiftSign * smoothShift * 0.025;

        const humanoid = this.vrm.humanoid;
        if (!humanoid) return;

        const hips = humanoid.getNormalizedBoneNode('hips');
        if (hips && Math.abs(pelvicTilt) > 0.001) {
            const qPelvis = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), pelvicTilt);
            hips.quaternion.slerp(qPelvis, 0.04);
        }
    }

    updateMicroBlinks(dt) {
        this.blinkTimer += dt;
        if (!this.isBlinking && this.blinkTimer >= this.nextBlinkInterval) {
            this.isBlinking = true;
            this.blinkProgress = 0.0;
            this.blinkTimer = 0.0;
            this.nextBlinkInterval = 2.5 + Math.random() * 4.0;
        }

        if (this.isBlinking) {
            this.blinkProgress += dt * 8.0;
            const blinkVal = Math.sin(Math.min(Math.PI, this.blinkProgress * Math.PI));
            if (this.vrm.expressionManager) {
                this.vrm.expressionManager.setValue('blink', blinkVal);
            }
            if (this.blinkProgress >= 1.0) {
                this.isBlinking = false;
                if (this.vrm.expressionManager) {
                    this.vrm.expressionManager.setValue('blink', 0.0);
                }
            }
        }
    }

    updateAttitudeFidgets(dt) {
        this.fidgetTimer += dt;
        if (this.activeFidget === 'none' && this.fidgetTimer >= this.nextFidgetInterval) {
            const fidgets = ['confidence_pose', 'head_curious', 'heel_bounce', 'hair_touch'];
            this.activeFidget = fidgets[Math.floor(Math.random() * fidgets.length)];
            this.fidgetProgress = 0.0;
            this.fidgetTimer = 0.0;
            this.nextFidgetInterval = 7.0 + Math.random() * 9.0;
        }

        if (this.activeFidget !== 'none') {
            this.fidgetProgress += dt * 0.55;
            const curve = Math.sin(Math.min(Math.PI, this.fidgetProgress * Math.PI));
            const humanoid = this.vrm.humanoid;
            if (humanoid) {
                if (this.activeFidget === 'confidence_pose') {
                    const head = humanoid.getNormalizedBoneNode('head');
                    if (head) {
                        const qHead = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.02, 0.04, 0.02, 'YXZ'));
                        head.quaternion.slerp(qHead, 0.08 * curve);
                    }
                } else if (this.activeFidget === 'head_curious') {
                    const head = humanoid.getNormalizedBoneNode('head');
                    if (head) {
                        const qHead = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.04, 0.08, 0.06, 'YXZ'));
                        head.quaternion.slerp(qHead, 0.10 * curve);
                    }
                }
            }

            if (this.fidgetProgress >= 1.0) {
                this.activeFidget = 'none';
            }
        }
    }

    updateCombatLayer(dt) {
        const targetBlend = this.combatStance ? 1.0 : 0.0;
        this.combatBlend += (targetBlend - this.combatBlend) * Math.min(1.0, dt * 6.0);

        if (this.combatBlend > 0.01) {
            const humanoid = this.vrm.humanoid;
            if (!humanoid) return;

            const spine = humanoid.getNormalizedBoneNode('spine');
            const lArm = humanoid.getNormalizedBoneNode('leftUpperArm');
            const rArm = humanoid.getNormalizedBoneNode('rightUpperArm');
            const lForearm = humanoid.getNormalizedBoneNode('leftLowerArm');
            const rForearm = humanoid.getNormalizedBoneNode('rightLowerArm');

            if (spine) {
                const qSpineCombat = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.12 * this.combatBlend, 0, 0, 'YXZ'));
                spine.quaternion.slerp(qSpineCombat, 0.18);
            }

            if (lArm && rArm) {
                const qLArmCombat = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.45 * this.combatBlend, 0, -0.45 * this.combatBlend, 'ZXY'));
                const qRArmCombat = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.45 * this.combatBlend, 0, 0.45 * this.combatBlend, 'ZXY'));
                lArm.quaternion.slerp(qLArmCombat, 0.20);
                rArm.quaternion.slerp(qRArmCombat, 0.20);
            }

            if (lForearm && rForearm) {
                const qLForearmCombat = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), 0.75 * this.combatBlend);
                const qRForearmCombat = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -0.75 * this.combatBlend);
                lForearm.quaternion.slerp(qLForearmCombat, 0.20);
                rForearm.quaternion.slerp(qRForearmCombat, 0.20);
            }
        }
    }

    updateSecondarySprings(dt) {
        if (!this.vrm || !this.vrm.springBoneManager) return;

        const humanoid = this.vrm.humanoid;
        if (!humanoid) return;

        const hips = humanoid.getNormalizedBoneNode('hips');
        if (!hips) return;

        const currentHipsPos = new THREE.Vector3();
        hips.getWorldPosition(currentHipsPos);

        const deltaPos = currentHipsPos.clone().sub(this.prevHipsPos);
        const velocity = deltaPos.clone().divideScalar(Math.max(0.001, dt));
        this.prevHipsPos.copy(currentHipsPos);

        const speed = velocity.length();
        if (speed > 0.05) {
            this.springStiffnessMultiplier = 0.85;
            this.springDragMultiplier = 0.90;
        } else {
            this.springStiffnessMultiplier = 1.0;
            this.springDragMultiplier = 1.0;
        }

        const joints = this.vrm.springBoneManager.joints || [];
        for (let i = 0; i < joints.length; i++) {
            const joint = joints[i];
            if (joint && joint.settings) {
                if (!joint._baseStiffness) {
                    joint._baseStiffness = joint.settings.stiffness || 1.0;
                    joint._baseDrag = joint.settings.dragForce || 0.4;
                }
                joint.settings.stiffness = joint._baseStiffness * this.springStiffnessMultiplier;
                joint.settings.dragForce = joint._baseDrag * this.springDragMultiplier;
            }
        }
    }
}
