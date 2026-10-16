import * as THREE from 'three';

export class FootIKSolver {
    constructor() {
        this.vrm = null;
        this.enabled = true;
        this.floorY = 0.0;
        this.leftLeg = null;
        this.rightLeg = null;
        this.hips = null;
        this.leftPlanted = false;
        this.rightPlanted = false;
        this.leftPlantPos = new THREE.Vector3();
        this.rightPlantPos = new THREE.Vector3();
        this.leftLastY = 0.0;
        this.rightLastY = 0.0;
        this.ikWeight = 0.0;
        this.targetIkWeight = 0.0;
        this.maxLegStretch = 0.96;
        this.groundThreshold = 0.038;
        this.hipsBaseY = 0.0;
        this.hipsOffset = 0.0;
        this.isLocomoting = false;
        this.isPerched = false;
    }

    setVrm(vrm) {
        this.vrm = vrm;
        this.leftLeg = null;
        this.rightLeg = null;
        this.hips = null;
        this.leftPlanted = false;
        this.rightPlanted = false;
        if (!vrm || !vrm.humanoid) return;

        const getBone = (name) => vrm.humanoid.getNormalizedBoneNode(name) || vrm.humanoid.getRawBoneNode(name);

        const leftUpper = getBone('leftUpperLeg');
        const leftLower = getBone('leftLowerLeg');
        const leftFoot = getBone('leftFoot');

        const rightUpper = getBone('rightUpperLeg');
        const rightLower = getBone('rightLowerLeg');
        const rightFoot = getBone('rightFoot');

        this.hips = getBone('hips');
        if (this.hips) {
            this.hipsBaseY = this.hips.position.y;
        }

        if (leftUpper && leftLower && leftFoot) {
            this.leftLeg = {
                upper: leftUpper,
                lower: leftLower,
                foot: leftFoot,
                l1: 0.42,
                l2: 0.40
            };
        }

        if (rightUpper && rightLower && rightFoot) {
            this.rightLeg = {
                upper: rightUpper,
                lower: rightLower,
                foot: rightFoot,
                l1: 0.42,
                l2: 0.40
            };
        }

        this.measureLengths();
    }

    measureLengths() {
        if (!this.vrm || !this.vrm.scene) return;
        this.vrm.scene.updateMatrixWorld(true);

        const v1 = new THREE.Vector3();
        const v2 = new THREE.Vector3();
        const v3 = new THREE.Vector3();

        if (this.leftLeg) {
            this.leftLeg.upper.getWorldPosition(v1);
            this.leftLeg.lower.getWorldPosition(v2);
            this.leftLeg.foot.getWorldPosition(v3);
            this.leftLeg.l1 = Math.max(0.2, v1.distanceTo(v2));
            this.leftLeg.l2 = Math.max(0.2, v2.distanceTo(v3));
            this.floorY = Math.min(this.floorY, v3.y);
        }

        if (this.rightLeg) {
            this.rightLeg.upper.getWorldPosition(v1);
            this.rightLeg.lower.getWorldPosition(v2);
            this.rightLeg.foot.getWorldPosition(v3);
            this.rightLeg.l1 = Math.max(0.2, v1.distanceTo(v2));
            this.rightLeg.l2 = Math.max(0.2, v2.distanceTo(v3));
            this.floorY = Math.min(this.floorY, v3.y);
        }
    }

    setIkWeight(weight) {
        this.targetIkWeight = Math.max(0.0, Math.min(1.0, Number(weight) || 0.0));
    }

    solveTwoBone(leg, targetPos, isPlanted, dt) {
        if (!leg || !this.vrm || !this.vrm.scene) return;

        const upper = leg.upper;
        const lower = leg.lower;
        const foot = leg.foot;
        const l1 = leg.l1;
        const l2 = leg.l2;

        const pUpper = new THREE.Vector3();
        const pLower = new THREE.Vector3();
        const pFoot = new THREE.Vector3();

        upper.getWorldPosition(pUpper);
        lower.getWorldPosition(pLower);
        foot.getWorldPosition(pFoot);

        const vArmTarget = new THREE.Vector3().subVectors(targetPos, pUpper);
        const totalLen = l1 + l2;
        let dist = vArmTarget.length();

        if (dist < 0.001) return;
        const maxDist = totalLen * this.maxLegStretch;
        dist = Math.min(dist, maxDist);

        const vCurrentFoot = new THREE.Vector3().subVectors(pFoot, pUpper);
        const curDist = Math.max(0.001, vCurrentFoot.length());

        const cosTargetLower = (l1 * l1 + l2 * l2 - dist * dist) / (2.0 * l1 * l2);
        const clampedCosTargetLower = Math.max(-1.0, Math.min(1.0, cosTargetLower));
        const angleTargetLower = Math.acos(clampedCosTargetLower);

        const cosCurLower = (l1 * l1 + l2 * l2 - curDist * curDist) / (2.0 * l1 * l2);
        const clampedCosCurLower = Math.max(-1.0, Math.min(1.0, cosCurLower));
        const angleCurLower = Math.acos(clampedCosCurLower);

        const deltaLower = (Math.PI - angleTargetLower) - (Math.PI - angleCurLower);

        const cosTargetUpper = (l1 * l1 + dist * dist - l2 * l2) / (2.0 * l1 * dist);
        const clampedCosTargetUpper = Math.max(-1.0, Math.min(1.0, cosTargetUpper));
        const angleTargetUpper = Math.acos(clampedCosTargetUpper);

        const cosCurUpper = (l1 * l1 + curDist * curDist - l2 * l2) / (2.0 * l1 * curDist);
        const clampedCosCurUpper = Math.max(-1.0, Math.min(1.0, cosCurUpper));
        const angleCurUpper = Math.acos(clampedCosCurUpper);

        const deltaUpperAngle = angleTargetUpper - angleCurUpper;

        if (vCurrentFoot.lengthSq() < 0.0001 || vArmTarget.lengthSq() < 0.0001) return;
        if (!isFinite(deltaUpperAngle) || !isFinite(deltaLower)) return;

        const vUpperToLower = new THREE.Vector3().subVectors(pLower, pUpper).normalize();
        const vLowerToFoot = new THREE.Vector3().subVectors(pFoot, pLower).normalize();

        let bendAxis = new THREE.Vector3().crossVectors(vUpperToLower, vLowerToFoot);
        if (bendAxis.lengthSq() < 0.0001) {
            const fwd = new THREE.Vector3(0, 0, 1);
            fwd.applyQuaternion(upper.parent ? upper.parent.getWorldQuaternion(new THREE.Quaternion()) : upper.quaternion);
            bendAxis.crossVectors(fwd, new THREE.Vector3(0, -1, 0));
        }
        bendAxis.normalize();

        const qAimIdentity = new THREE.Quaternion();
        const qAim = new THREE.Quaternion().setFromUnitVectors(
            vCurrentFoot.clone().normalize(),
            vArmTarget.clone().normalize()
        );
        qAim.slerp(qAimIdentity, 1.0 - this.ikWeight);

        const qUpperHinge = new THREE.Quaternion().setFromAxisAngle(bendAxis, deltaUpperAngle * this.ikWeight);
        const qUpperDeltaWorld = qAim.clone().multiply(qUpperHinge);

        const parentUpperQ = new THREE.Quaternion();
        if (upper.parent) {
            upper.parent.getWorldQuaternion(parentUpperQ);
        }
        const invParentUpperQ = parentUpperQ.clone().invert();
        const localUpperDelta = invParentUpperQ.clone().multiply(qUpperDeltaWorld).multiply(parentUpperQ);
        if (!isFinite(localUpperDelta.x) || !isFinite(localUpperDelta.y) || !isFinite(localUpperDelta.z) || !isFinite(localUpperDelta.w)) return;

        upper.quaternion.premultiply(localUpperDelta);
        upper.updateMatrixWorld(true);

        const qLowerDeltaWorld = new THREE.Quaternion().setFromAxisAngle(bendAxis, deltaLower * this.ikWeight);
        const parentLowerQ = new THREE.Quaternion();
        if (lower.parent) {
            lower.parent.getWorldQuaternion(parentLowerQ);
        }
        const invParentLowerQ = parentLowerQ.clone().invert();
        const localLowerDelta = invParentLowerQ.clone().multiply(qLowerDeltaWorld).multiply(parentLowerQ);
        if (!isFinite(localLowerDelta.x) || !isFinite(localLowerDelta.y) || !isFinite(localLowerDelta.z) || !isFinite(localLowerDelta.w)) return;

        lower.quaternion.premultiply(localLowerDelta);
        lower.updateMatrixWorld(true);

        if (isPlanted) {
            const footTargetQ = new THREE.Quaternion();
            foot.getWorldQuaternion(footTargetQ);
            const euler = new THREE.Euler().setFromQuaternion(footTargetQ, 'YXZ');
            euler.x = 0;
            euler.z = 0;
            footTargetQ.setFromEuler(euler);

            const parentFootQ = new THREE.Quaternion();
            if (foot.parent) {
                foot.parent.getWorldQuaternion(parentFootQ);
            }
            const localFootQ = parentFootQ.clone().invert().multiply(footTargetQ);
            foot.quaternion.slerp(localFootQ, this.ikWeight * 0.85);
            foot.updateMatrixWorld(true);
        }
    }

    update(dt) {
        if (!this.enabled || !this.vrm || !this.vrm.scene) return;

        if (!this.isPerched) {
            this.targetIkWeight = 0.0;
        }

        if (this.ikWeight !== this.targetIkWeight) {
            const step = dt * 6.0;
            if (this.ikWeight < this.targetIkWeight) {
                this.ikWeight = Math.min(this.targetIkWeight, this.ikWeight + step);
            } else {
                this.ikWeight = Math.max(this.targetIkWeight, this.ikWeight - step);
            }
        }

        if (this.ikWeight < 0.01) {
            this.leftPlanted = false;
            this.rightPlanted = false;
            return;
        }
        if (this.isPerched) {
            this.leftPlanted = false;
            this.rightPlanted = false;
            return;
        }

        this.vrm.scene.updateMatrixWorld(true);

        const pLeftFoot = new THREE.Vector3();
        const pRightFoot = new THREE.Vector3();

        if (this.leftLeg) this.leftLeg.foot.getWorldPosition(pLeftFoot);
        if (this.rightLeg) this.rightLeg.foot.getWorldPosition(pRightFoot);

        const leftTarget = pLeftFoot.clone();
        const rightTarget = pRightFoot.clone();

        const leftDistFloor = pLeftFoot.y - this.floorY;
        const rightDistFloor = pRightFoot.y - this.floorY;

        const leftVelY = (pLeftFoot.y - this.leftLastY) / Math.max(0.001, dt);
        const rightVelY = (pRightFoot.y - this.rightLastY) / Math.max(0.001, dt);

        this.leftLastY = pLeftFoot.y;
        this.rightLastY = pRightFoot.y;

        if (this.isLocomoting) {
            this.leftPlanted = false;
            this.rightPlanted = false;
            leftTarget.copy(pLeftFoot);
            rightTarget.copy(pRightFoot);
            leftTarget.y = Math.max(this.floorY, pLeftFoot.y);
            rightTarget.y = Math.max(this.floorY, pRightFoot.y);
        } else {
            if (leftDistFloor <= this.groundThreshold && leftVelY <= 0.05) {
                if (!this.leftPlanted) {
                    this.leftPlanted = true;
                    this.leftPlantPos.copy(pLeftFoot);
                    this.leftPlantPos.y = this.floorY;
                }
            } else if (leftDistFloor > this.groundThreshold * 1.6 || leftVelY > 0.12) {
                this.leftPlanted = false;
            }

            if (rightDistFloor <= this.groundThreshold && rightVelY <= 0.05) {
                if (!this.rightPlanted) {
                    this.rightPlanted = true;
                    this.rightPlantPos.copy(pRightFoot);
                    this.rightPlantPos.y = this.floorY;
                }
            } else if (rightDistFloor > this.groundThreshold * 1.6 || rightVelY > 0.12) {
                this.rightPlanted = false;
            }

            if (this.leftLeg && this.leftPlanted) {
                const pUpperL = new THREE.Vector3();
                this.leftLeg.upper.getWorldPosition(pUpperL);
                const distFromHip = pUpperL.distanceTo(this.leftPlantPos);
                if (distFromHip > (this.leftLeg.l1 + this.leftLeg.l2) * 0.95) {
                    this.leftPlanted = false;
                } else {
                    leftTarget.copy(this.leftPlantPos);
                }
            }

            if (this.rightLeg && this.rightPlanted) {
                const pUpperR = new THREE.Vector3();
                this.rightLeg.upper.getWorldPosition(pUpperR);
                const distFromHip = pUpperR.distanceTo(this.rightPlantPos);
                if (distFromHip > (this.rightLeg.l1 + this.rightLeg.l2) * 0.95) {
                    this.rightPlanted = false;
                } else {
                    rightTarget.copy(this.rightPlantPos);
                }
            }

            leftTarget.y = Math.max(this.floorY, leftTarget.y);
            rightTarget.y = Math.max(this.floorY, rightTarget.y);
        }

        if (this.leftLeg && this.rightLeg) {
            const pUpperL = new THREE.Vector3();
            const pUpperR = new THREE.Vector3();
            this.leftLeg.upper.getWorldPosition(pUpperL);
            this.rightLeg.upper.getWorldPosition(pUpperR);

            const hipAxis = new THREE.Vector3().subVectors(pUpperL, pUpperR);
            const hipDistance = hipAxis.length();
            if (hipDistance > 0.05) {
                hipAxis.normalize();
                const hipCenter = new THREE.Vector3().addVectors(pUpperL, pUpperR).multiplyScalar(0.5);

                const leftProj = new THREE.Vector3().subVectors(leftTarget, hipCenter).dot(hipAxis);
                const rightProj = new THREE.Vector3().subVectors(rightTarget, hipCenter).dot(hipAxis);

                const minSeparation = Math.max(0.04, hipDistance * 0.25);
                const maxSeparation = Math.max(0.09, hipDistance * 0.55);

                if (leftProj < minSeparation) {
                    leftTarget.addScaledVector(hipAxis, minSeparation - leftProj);
                } else if (leftProj > maxSeparation) {
                    leftTarget.addScaledVector(hipAxis, maxSeparation - leftProj);
                }

                if (rightProj > -minSeparation) {
                    rightTarget.addScaledVector(hipAxis, -minSeparation - rightProj);
                } else if (rightProj < -maxSeparation) {
                    rightTarget.addScaledVector(hipAxis, -maxSeparation - rightProj);
                }
            }
        }

        let targetHipsOffset = 0.0;
        if (this.leftPlanted && this.rightPlanted) {
            const lowestTargetY = Math.min(leftTarget.y, rightTarget.y);
            if (lowestTargetY > this.floorY + 0.01) {
                targetHipsOffset = lowestTargetY - this.floorY;
            }
        }
        this.hipsOffset += (targetHipsOffset - this.hipsOffset) * Math.min(1.0, dt * 8.0);
        if (this.hips) {
            this.hips.position.y = this.hipsBaseY + this.hipsOffset;
        }

        if (this.leftLeg) {
            this.solveTwoBone(this.leftLeg, leftTarget, this.leftPlanted, dt);
        }
        if (this.rightLeg) {
            this.solveTwoBone(this.rightLeg, rightTarget, this.rightPlanted, dt);
        }
    }
}
