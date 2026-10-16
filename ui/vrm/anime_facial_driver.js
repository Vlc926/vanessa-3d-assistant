import * as THREE from 'three';

export class AnimeFacialDriver {
    constructor() {
        this.vrm = null;
        this.enabled = true;
        this.snapThreshold = 0.72;
        this.blendSpeed = 14.0;

        this.targetMorphs = new Map();
        this.currentMorphs = new Map();

        this.leftPupilOffset = new THREE.Vector2(0, 0);
        this.rightPupilOffset = new THREE.Vector2(0, 0);
        this.targetPupilOffset = new THREE.Vector2(0, 0);

        this.meshMorphMap = new Map();
        this.supportedExpressions = new Set();

        this.microTimer = 0.0;
        this.microBlinkTimer = 0.0;
        this.nextMicroBlink = 3.2;
        this.microBrowOffset = 0.0;
        this.microSmileOffset = 0.0;

        this.asymmetricPresets = {
            smug: {
                happy: 0.55,
                relaxed: 0.45,
                blinkLeft: 0.22,
                Fcl_MTH_Fun: 0.6,
                Fcl_EYE_Close_L: 0.25,
                Fcl_BRW_Joy: 0.4
            },
            winking: {
                blinkLeft: 1.0,
                blinkRight: 0.0,
                happy: 0.70,
                relaxed: 0.30,
                Fcl_EYE_Close_L: 1.0,
                Fcl_MTH_Joy: 0.7
            },
            shocked: {
                surprised: 1.0,
                aa: 0.55,
                blink: 0.0,
                Fcl_ALL_Surprised: 0.95,
                Fcl_MTH_A: 0.5
            },
            pout: {
                angry: 0.35,
                sad: 0.45,
                ou: 0.55,
                Fcl_MTH_U: 0.6,
                Fcl_BRW_Angry: 0.4
            },
            dramatic_smirk: {
                happy: 0.65,
                blinkLeft: 0.30,
                relaxed: 0.40,
                Fcl_MTH_Fun: 0.75,
                Fcl_EYE_Close_L: 0.35
            },
            embarrassed: {
                happy: 0.30,
                sad: 0.35,
                blink: 0.25,
                relaxed: 0.20,
                Fcl_BRW_Sorrow: 0.3
            },
            sleepy: {
                blink: 0.65,
                relaxed: 0.40,
                Fcl_EYE_Close: 0.65
            },
            thinking: {
                surprised: 0.25,
                relaxed: 0.35,
                blinkRight: 0.18,
                Fcl_BRW_Joy: 0.3
            }
        };

        this.aliasMap = {
            joy: ['happy', 'Joy', 'joy', 'Fcl_ALL_Joy', 'Fcl_EYE_Joy', 'Fcl_MTH_Joy'],
            happy: ['happy', 'Joy', 'joy', 'Fcl_ALL_Joy', 'Fcl_EYE_Joy', 'Fcl_MTH_Joy'],
            fun: ['relaxed', 'Fun', 'fun', 'Fcl_ALL_Fun', 'Fcl_MTH_Fun'],
            relaxed: ['relaxed', 'Fun', 'fun', 'Fcl_ALL_Fun', 'Fcl_MTH_Fun'],
            angry: ['angry', 'Angry', 'Fcl_ALL_Angry', 'Fcl_BRW_Angry', 'Fcl_MTH_Angry'],
            sorrow: ['sad', 'Sorrow', 'sorrow', 'Fcl_ALL_Sorrow', 'Fcl_BRW_Sorrow'],
            sad: ['sad', 'Sorrow', 'sorrow', 'Fcl_ALL_Sorrow', 'Fcl_BRW_Sorrow'],
            surprised: ['surprised', 'Surprised', 'Fcl_ALL_Surprised', 'Fcl_EYE_Surprised'],
            blink: ['blink', 'Blink', 'Fcl_EYE_Close'],
            blinkleft: ['blinkLeft', 'Blink_L', 'blink_l', 'Fcl_EYE_Close_L'],
            blinkright: ['blinkRight', 'Blink_R', 'blink_r', 'Fcl_EYE_Close_R'],
            aa: ['aa', 'A', 'Fcl_MTH_A'],
            ih: ['ih', 'I', 'Fcl_MTH_I'],
            ou: ['ou', 'U', 'Fcl_MTH_U'],
            ee: ['ee', 'E', 'Fcl_MTH_E'],
            oh: ['oh', 'O', 'Fcl_MTH_O']
        };
    }

    setVrm(vrm) {
        this.vrm = vrm;
        this.targetMorphs.clear();
        this.currentMorphs.clear();
        this.meshMorphMap.clear();
        this.supportedExpressions.clear();
        if (!vrm) return;

        this.catalogModelExpressions(vrm);
        this.optimizeMToonNormals(vrm);
    }

    catalogModelExpressions(vrm) {
        if (!vrm) return;

        if (vrm.expressionManager) {
            const expMgr = vrm.expressionManager;
            if (expMgr.expressions) {
                expMgr.expressions.forEach(exp => {
                    if (exp && exp.expressionName) {
                        this.supportedExpressions.add(exp.expressionName.toLowerCase());
                    }
                });
            }
            const candidateNames = [
                'happy', 'joy', 'angry', 'sad', 'sorrow', 'relaxed', 'fun', 'surprised', 'neutral',
                'blink', 'blinkLeft', 'blinkRight', 'Blink', 'Blink_L', 'Blink_R',
                'Joy', 'Angry', 'Sorrow', 'Fun', 'Surprised', 'Neutral',
                'aa', 'ih', 'ou', 'ee', 'oh', 'A', 'I', 'U', 'E', 'O', 'Extra'
            ];
            candidateNames.forEach(name => {
                try {
                    const track = expMgr.getExpression(name);
                    if (track) {
                        this.supportedExpressions.add(name.toLowerCase());
                    }
                } catch (e) {}
            });
        }

        if (vrm.scene) {
            vrm.scene.traverse(node => {
                if (node.isMesh && node.morphTargetDictionary && node.morphTargetInfluences) {
                    for (const [targetName, idx] of Object.entries(node.morphTargetDictionary)) {
                        const lower = targetName.toLowerCase();
                        if (!this.meshMorphMap.has(lower)) {
                            this.meshMorphMap.set(lower, []);
                        }
                        this.meshMorphMap.get(lower).push({ mesh: node, index: idx });
                    }
                }
            });
        }
    }

    optimizeMToonNormals(vrm) {
        if (!vrm || !vrm.scene) return;
        vrm.scene.traverse((obj) => {
            if (obj.isMesh && obj.material) {
                const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
                materials.forEach(mat => {
                    if (mat.isMToonMaterial || mat.type === 'ShaderMaterial' || mat.type === 'MeshStandardMaterial') {
                        mat.flatShading = false;
                        if (mat.userData && mat.userData.vrmMToonMaterial) {
                            mat.userData.vrmMToonMaterial.shadeShift = 0.05;
                            mat.userData.vrmMToonMaterial.shadeToony = 0.95;
                        }
                    }
                });
            }
        });
    }

    setAsymmetricPreset(name, intensity = 1.0) {
        const preset = this.asymmetricPresets[name];
        if (!preset) return;

        const factor = Math.max(0.0, Math.min(1.0, intensity));
        for (const [morphKey, targetVal] of Object.entries(preset)) {
            this.setMorph(morphKey, targetVal * factor, factor >= this.snapThreshold);
        }
    }

    setMorph(name, weight, snap = false) {
        const target = Math.max(0.0, Math.min(1.0, Number(weight) || 0.0));
        this.targetMorphs.set(name, target);

        if (snap) {
            this.currentMorphs.set(name, target);
            this._applyRawMorph(name, target);
        }
    }

    resetMorphs() {
        this.targetMorphs.forEach((_, key) => {
            this.targetMorphs.set(key, 0.0);
        });
    }

    setDecoupledGaze(x, y, instant = false) {
        const clampX = Math.max(-0.6, Math.min(0.6, Number(x) || 0.0));
        const clampY = Math.max(-0.4, Math.min(0.4, Number(y) || 0.0));
        this.targetPupilOffset.set(clampX, clampY);

        if (instant) {
            this.leftPupilOffset.copy(this.targetPupilOffset);
            this.rightPupilOffset.copy(this.targetPupilOffset);
        }
    }

    update(dt) {
        if (!this.enabled || !this.vrm || !this.vrm.scene) return;

        const safeDt = Math.max(0.001, Math.min(0.05, dt));

        this.leftPupilOffset.lerp(this.targetPupilOffset, Math.min(1.0, safeDt * 24.0));
        this.rightPupilOffset.lerp(this.targetPupilOffset, Math.min(1.0, safeDt * 24.0));

        this.microTimer += safeDt;
        this.microBrowOffset = Math.sin(this.microTimer * 0.8) * 0.04;
        this.microSmileOffset = Math.max(0.0, Math.sin(this.microTimer * 0.4) * 0.06);

        this.targetMorphs.forEach((targetWeight, morphName) => {
            let current = this.currentMorphs.get(morphName) || 0.0;
            let finalTarget = targetWeight;

            if (morphName === 'happy' || morphName === 'joy') {
                finalTarget = Math.min(1.0, finalTarget + this.microSmileOffset);
            }

            if (Math.abs(current - finalTarget) > 0.002) {
                current += (finalTarget - current) * Math.min(1.0, safeDt * this.blendSpeed);
                this.currentMorphs.set(morphName, current);
                this._applyRawMorph(morphName, current);
            }
        });
    }

    _applyRawMorph(name, weight) {
        if (!this.vrm) return;

        const clampedWeight = Math.max(0.0, Math.min(1.0, Number(weight) || 0.0));
        const lower = name.toLowerCase();

        let applied = false;
        if (this.vrm.expressionManager) {
            const expMgr = this.vrm.expressionManager;
            if (this.supportedExpressions.has(lower)) {
                try {
                    expMgr.setValue(name, clampedWeight);
                    applied = true;
                } catch (e) {}
            }
            if (!applied && this.aliasMap[lower]) {
                const aliases = this.aliasMap[lower];
                for (let i = 0; i < aliases.length; i++) {
                    const alias = aliases[i];
                    if (this.supportedExpressions.has(alias.toLowerCase())) {
                        try {
                            expMgr.setValue(alias, clampedWeight);
                            applied = true;
                            break;
                        } catch (e) {}
                    }
                }
            }
        }

        if (this.meshMorphMap.has(lower)) {
            const entries = this.meshMorphMap.get(lower);
            for (let i = 0; i < entries.length; i++) {
                const item = entries[i];
                if (item.mesh && item.mesh.morphTargetInfluences) {
                    item.mesh.morphTargetInfluences[item.index] = clampedWeight;
                    applied = true;
                }
            }
        } else if (!applied && this.aliasMap[lower]) {
            const aliases = this.aliasMap[lower];
            for (let i = 0; i < aliases.length; i++) {
                const aLower = aliases[i].toLowerCase();
                if (this.meshMorphMap.has(aLower)) {
                    const entries = this.meshMorphMap.get(aLower);
                    for (let j = 0; j < entries.length; j++) {
                        const item = entries[j];
                        if (item.mesh && item.mesh.morphTargetInfluences) {
                            item.mesh.morphTargetInfluences[item.index] = clampedWeight;
                            applied = true;
                        }
                    }
                    if (applied) break;
                }
            }
        }
    }
}
