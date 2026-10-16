import * as THREE from 'three';
import { MOTION_DEFINITIONS, getMotionConfig } from './personality_kinematics.js';

export class MotionMatchingEngine {
    constructor(animController, footIkSolver) {
        this.animController = animController;
        this.footIkSolver = footIkSolver;

        this.desiredVelocity = new THREE.Vector2(0, 0);
        this.currentVelocity = new THREE.Vector2(0, 0);
        this.targetSpeed = 0.0;
        this.currentSpeed = 0.0;

        this.cognitiveIntent = 'idle';
        this.emotionalState = 'neutral';
        this.postureIntent = 'standby';
        this.urgency = 1.0;

        this.facingYaw = 0.0;
        this.targetYaw = 0.0;
        this.turnSpeed = 6.0;

        this.activeMotionId = 'idle';
        this.isLocomoting = false;
        this.isPerched = false;
        this.timeSinceLastMatch = 0.0;
        this.matchInterval = 0.12;

        this.isReading = false;
        this.readSaccadeTimer = 0.0;
        this.readSaccadeTargetX = 0.0;
        this.readSaccadeCurrentX = 0.0;
        this.readSaccadeTargetY = 0.0;

        this.blinkTimer = 2.0 + Math.random() * 3.0;
        this.blinkDuration = 0.16;
        this.blinkElapsed = 0.0;
        this.isBlinking = false;

        this.onExpressionTrigger = null;
        this.onEventTrigger = null;
    }

    setPerched(perched, perchStyle = 'sit') {
        this.isPerched = Boolean(perched);
        this.targetYaw = 0.0;
        this.desiredVelocity.set(0, 0);
        this.targetSpeed = 0.0;
        if (this.footIkSolver) {
            this.footIkSolver.isPerched = this.isPerched;
        }
        if (this.isPerched) {
            this.postureIntent = 'perched';
            const motionKey = perchStyle === 'dangle' ? 'perch_window_dangle'
                : (perchStyle === 'crouch' ? 'perch_edge_crouch' : 'perch_window_sit');
            this.transitionToMotion(motionKey);
            this.dispatchKinematicEvent('onPerch', { style: perchStyle });
        } else {
            this.postureIntent = 'standby';
            this.transitionToMotion('idle');
            this.dispatchKinematicEvent('onUnperch', {});
        }
    }

    setReadingMode(reading) {
        this.isReading = Boolean(reading);
        if (this.isReading) {
            this.cognitiveIntent = 'reading';
            this.transitionToMotion('inspect_window_read');
        } else if (this.cognitiveIntent === 'reading') {
            this.cognitiveIntent = 'idle';
            this.transitionToMotion('idle');
        }
    }

    dispatchKinematicEvent(name, data = {}) {
        if (this.onEventTrigger) {
            this.onEventTrigger(name, data);
        }
    }

    receiveMotorCommand(intent, vx, vy, speed, mood, posture) {
        if (intent) this.cognitiveIntent = String(intent).toLowerCase();
        if (mood) this.emotionalState = String(mood).toLowerCase();
        if (posture) this.postureIntent = String(posture).toLowerCase();

        this.targetSpeed = Math.max(0.0, Math.min(2.5, Number(speed) || 0.0));
        this.desiredVelocity.set(Number(vx) || 0.0, Number(vy) || 0.0);

        if (this.desiredVelocity.lengthSq() > 0.001) {
            const turnAngle = Math.sign(this.desiredVelocity.x) * 0.40;
            this.targetYaw = 0.0 + turnAngle;
            this.postureIntent = 'locomotion';
            if (this.isPerched) {
                this.setPerched(false);
            }
        } else if (this.targetSpeed > 0.05) {
            this.postureIntent = 'locomotion';
            if (this.isPerched) {
                this.setPerched(false);
            }
        } else {
            this.targetYaw = 0.0;
        }

        this.evaluateMotionMatch(true);
    }

    setGazeDirection(lookX, lookY) {
        if (Math.abs(lookX) > 0.15) {
            const yawOffset = (lookX - 0.5) * 0.45;
            this.targetYaw = 0.0 + yawOffset;
        }
    }

    computeCandidateCost(candidateKey, candidateDef) {
        let cost = 0.0;

        const isCandidateLoco = candidateKey.includes('walk') || candidateKey.includes('step');
        const isQueryLoco = this.postureIntent === 'locomotion' || this.currentSpeed > 0.15;

        if (isQueryLoco !== isCandidateLoco) {
            cost += 10.0;
        }

        if (this.postureIntent === 'perched') {
            if (candidateDef.isPerched || candidateKey.includes('perch')) {
                cost -= 15.0;
            } else {
                cost += 25.0;
            }
        } else if (this.postureIntent === 'sitting') {
            if (candidateKey.includes('sit')) {
                cost -= 8.0;
            } else {
                cost += 15.0;
            }
        } else if (this.postureIntent === 'crouch') {
            if (candidateKey.includes('crouch') || candidateKey.includes('squat')) {
                cost -= 8.0;
            } else {
                cost += 15.0;
            }
        }

        if (this.cognitiveIntent && this.cognitiveIntent !== 'idle') {
            if (candidateKey === this.cognitiveIntent) {
                cost -= 14.0;
            } else if (candidateKey.includes(this.cognitiveIntent)) {
                cost -= 7.0;
            }
        }

        if (isQueryLoco && isCandidateLoco) {
            const idealSpeed = candidateDef.speed || 1.0;
            cost += Math.abs(idealSpeed - this.currentSpeed) * 3.0;
        }

        if (candidateKey === this.activeMotionId) {
            cost -= 1.5;
        }

        return cost;
    }

    evaluateMotionMatch(force = false) {
        let bestKey = this.activeMotionId;
        let lowestCost = 999.0;

        const candidateKeys = Object.keys(MOTION_DEFINITIONS);
        for (let i = 0; i < candidateKeys.length; i++) {
            const key = candidateKeys[i];
            const def = MOTION_DEFINITIONS[key];
            const c = this.computeCandidateCost(key, def);
            if (c < lowestCost) {
                lowestCost = c;
                bestKey = key;
            }
        }

        if (bestKey && (bestKey !== this.activeMotionId || force)) {
            this.transitionToMotion(bestKey);
        }
    }

    transitionToMotion(motionKey) {
        const config = getMotionConfig(motionKey);
        if (!config) return;

        this.activeMotionId = motionKey;
        this.isLocomoting = motionKey.includes('walk') || motionKey.includes('step');

        if (this.footIkSolver) {
            this.footIkSolver.isLocomoting = this.isLocomoting;
            this.footIkSolver.isPerched = this.isPerched || Boolean(config.isPerched);
            if (this.isLocomoting) {
                this.footIkSolver.setIkWeight(0.0);
            } else if (this.isPerched || motionKey.includes('sit') || motionKey.includes('crouch') || motionKey.includes('think') || motionKey.includes('dance') || motionKey.includes('cheer') || motionKey.includes('cross') || motionKey.includes('blush') || motionKey.includes('pat') || motionKey.includes('fidget')) {
                this.footIkSolver.setIkWeight(0.0);
            } else {
                this.footIkSolver.setIkWeight(0.0);
            }
        }

        let blendTime = 0.38;
        if (this.isLocomoting) {
            blendTime = 0.32;
            this.animController.setWalkSpeed(Math.max(0.7, this.currentSpeed || 1.0));
        } else if (config.loop) {
            blendTime = 0.48;
        } else {
            blendTime = 0.42;
        }

        this.animController.playMotion(motionKey, blendTime);

        if (this.onExpressionTrigger) {
            const expr = config.expr || this.emotionalState || 'neutral';
            const weight = config.weight || 0.85;
            this.onExpressionTrigger(expr, weight);
        }

        this.dispatchKinematicEvent('onMotionChange', { motion: motionKey });
    }

    updateProceduralFacial(dt, vrm) {
        if (!vrm || !vrm.expressionManager) return;

        this.blinkTimer -= dt;
        if (this.blinkTimer <= 0 && !this.isBlinking) {
            this.isBlinking = true;
            this.blinkElapsed = 0.0;
        }

        if (this.isBlinking) {
            this.blinkElapsed += dt;
            const progress = this.blinkElapsed / this.blinkDuration;
            let blinkWeight = 0.0;
            if (progress <= 0.5) {
                blinkWeight = progress / 0.5;
            } else if (progress <= 1.0) {
                blinkWeight = 1.0 - ((progress - 0.5) / 0.5);
            } else {
                this.isBlinking = false;
                this.blinkTimer = 2.5 + Math.random() * 4.0;
                blinkWeight = 0.0;
            }
            try {
                vrm.expressionManager.setValue('blink', blinkWeight);
            } catch (e) {}
        }

        if (this.isReading && vrm.lookAt) {
            this.readSaccadeTimer += dt;
            if (this.readSaccadeTimer >= 0.25) {
                this.readSaccadeTimer = 0.0;
                this.readSaccadeTargetX += 0.22;
                if (this.readSaccadeTargetX > 0.45) {
                    this.readSaccadeTargetX = -0.45;
                    this.readSaccadeTargetY = (Math.random() - 0.5) * 0.15;
                }
            }
            this.readSaccadeCurrentX += (this.readSaccadeTargetX - this.readSaccadeCurrentX) * Math.min(1.0, dt * 14.0);
            try {
                vrm.lookAt.lookAt(new THREE.Vector3(this.readSaccadeCurrentX, this.readSaccadeTargetY - 0.2, -1.0));
            } catch (e) {}
        }
    }

    update(dt, vrm) {
        if (!vrm || !vrm.scene) return;
        if (this.footIkSolver) {
            this.footIkSolver.isLocomoting = this.isLocomoting;
            this.footIkSolver.isPerched = this.isPerched;
        }

        const accelRate = 7.0;
        this.currentVelocity.lerp(this.desiredVelocity, Math.min(1.0, dt * accelRate));
        this.currentSpeed = this.currentVelocity.length();

        if (this.targetSpeed > 0.001 && this.currentSpeed < 0.05) {
            this.currentSpeed = this.targetSpeed;
        }

        let diffYaw = this.targetYaw - this.facingYaw;
        while (diffYaw > Math.PI) diffYaw -= Math.PI * 2;
        while (diffYaw < -Math.PI) diffYaw += Math.PI * 2;
        this.facingYaw += diffYaw * Math.min(1.0, dt * this.turnSpeed);
        const baseRot = Math.PI;
        vrm.scene.rotation.y = baseRot + this.facingYaw;

        this.updateProceduralFacial(dt, vrm);

        this.timeSinceLastMatch += dt;
        if (this.timeSinceLastMatch >= this.matchInterval) {
            this.timeSinceLastMatch = 0.0;
            this.evaluateMotionMatch(false);
        }
    }
}
