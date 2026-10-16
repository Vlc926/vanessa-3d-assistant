import * as THREE from 'three';
import { ExpressionBlender } from './ExpressionBlender.js';

export class AnimeFacialDriver {
    constructor() {
        this.vrm = null;
        this.enabled = true;
        this.snapThreshold = 0.72;
        this.blendSpeed = 14.0;

        this.blender = new ExpressionBlender();

        this.targetMorphs = new Map();
        this.currentMorphs = new Map();

        this.leftPupilOffset = new THREE.Vector2(0, 0);
        this.rightPupilOffset = new THREE.Vector2(0, 0);
        this.targetPupilOffset = new THREE.Vector2(0, 0);
        this.pupilScale = 1.0;
        this.targetPupilScale = 1.0;

        this.secondaryFacialBones = {
            jaw: null,
            tongue: null,
            leftCheek: null,
            rightCheek: null,
            leftEye: null,
            rightEye: null
        };
        this.targetSecondaryState = {
            jawPitch: 0.0,
            tongueOut: 0.0,
            cheekPuff: 0.0,
            browAsymmetry: 0.0
        };

        this.meshMorphMap = new Map();
        this.supportedExpressions = new Set();

        this.microTimer = 0.0;
        this.microBlinkTimer = 0.0;
        this.nextMicroBlink = 3.2;
        this.microBrowOffset = 0.0;
        this.microSmileOffset = 0.0;

        this.learnedExpressions = [];
        this.onLearnedBehaviorSynthesized = null;

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
            },
            cat_smile: {
                happy: 0.75,
                relaxed: 0.50,
                blinkLeft: 0.15,
                _mouthPress_CatMouth: 0.70
            }
        };

        this.aliasMap = {
            joy: ['happy', 'Joy', 'joy', 'Fcl_ALL_Joy', 'Fcl_EYE_Joy', 'Fcl_MTH_Joy', '笑顔', '笑い', 'にこり'],
            happy: ['happy', 'Joy', 'joy', 'Fcl_ALL_Joy', 'Fcl_EYE_Joy', 'Fcl_MTH_Joy', '笑顔', '笑い', 'にこり'],
            fun: ['relaxed', 'Fun', 'fun', 'Fcl_ALL_Fun', 'Fcl_MTH_Fun', 'なごみ'],
            relaxed: ['relaxed', 'Fun', 'fun', 'Fcl_ALL_Fun', 'Fcl_MTH_Fun', 'なごみ', '穏やか'],
            angry: ['angry', 'Angry', 'Fcl_ALL_Angry', 'Fcl_BRW_Angry', 'Fcl_MTH_Angry', '怒り'],
            sorrow: ['sad', 'Sorrow', 'sorrow', 'Fcl_ALL_Sorrow', 'Fcl_BRW_Sorrow', '困る', '悲しい'],
            sad: ['sad', 'Sorrow', 'sorrow', 'Fcl_ALL_Sorrow', 'Fcl_BRW_Sorrow', '困る', '悲しい'],
            surprised: ['surprised', 'Surprised', 'Fcl_ALL_Surprised', 'Fcl_EYE_Surprised', 'びっくり', '驚き'],
            blink: ['blink', 'Blink', 'Fcl_EYE_Close', 'まばたき'],
            blinkleft: ['blinkLeft', 'Blink_L', 'blink_l', 'Fcl_EYE_Close_L', 'ウィンク'],
            blinkright: ['blinkRight', 'Blink_R', 'blink_r', 'Fcl_EYE_Close_R', 'ウィンク右'],
            aa: ['aa', 'A', 'Fcl_MTH_A', 'あ'],
            ih: ['ih', 'I', 'Fcl_MTH_I', 'い'],
            ou: ['ou', 'U', 'Fcl_MTH_U', 'う'],
            ee: ['ee', 'E', 'Fcl_MTH_E', 'え'],
            oh: ['oh', 'O', 'Fcl_MTH_O', 'お'],
            shy: ['shy', '照れ', 'テレ', '赤面', 'チーク', 'Blush']
        };

        this.loadLearnedBehaviors();
    }

    loadLearnedBehaviors() {
        if (typeof fetch !== 'function') return;
        fetch('/config/learned_behaviors.json')
            .then(r => (r && r.ok ? r.json() : null))
            .then(data => {
                if (data && Array.isArray(data.learned_expressions)) {
                    this.learnedExpressions = data.learned_expressions;
                    for (const item of data.learned_expressions) {
                        if (item && item.id && item.morphs) {
                            this.asymmetricPresets[item.id] = item.morphs;
                            if (this.blender && this.blender.presets) {
                                this.blender.presets[item.id] = item.morphs;
                            }
                        }
                    }
                }
            })
            .catch(() => {});
    }

    synthesizeEvolutionaryPreset(basePresetName, intensity = 1.0) {
        const base = this.asymmetricPresets[basePresetName] || this.asymmetricPresets.smug;
        const jitter = () => (Math.random() - 0.5) * 0.14;
        const morphs = {};
        for (const [k, v] of Object.entries(base)) {
            morphs[k] = Number(Math.max(0.0, Math.min(1.0, (v + jitter()) * intensity)).toFixed(3));
        }
        const id = `synth_${basePresetName}_${Date.now()}`;
        this.asymmetricPresets[id] = morphs;
        if (this.blender && this.blender.presets) {
            this.blender.presets[id] = morphs;
        }
        const entry = {
            id,
            context: basePresetName,
            morphs,
            secondary_bones: {
                jawOpen: Number((Math.max(0, morphs.aa || 0) * 0.25).toFixed(3)),
                pupilScale: Number((1.0 + (morphs.surprised || 0) * 0.15).toFixed(3)),
                browAsymmetry: Number(jitter().toFixed(3))
            },
            body_posture: {
                spinePitch: Number((jitter() * 0.4).toFixed(3)),
                headTiltZ: Number((jitter() * 0.6).toFixed(3)),
                shoulderLift: Number((Math.abs(jitter()) * 0.3).toFixed(3)),
                clip: 'idle_loop'
            }
        };
        this.learnedExpressions.push(entry);
        if (typeof this.onLearnedBehaviorSynthesized === 'function') {
            this.onLearnedBehaviorSynthesized(entry);
        }
        return entry;
    }

    setVrm(vrm) {
        this.vrm = vrm;
        this.targetMorphs.clear();
        this.currentMorphs.clear();
        this.meshMorphMap.clear();
        this.supportedExpressions.clear();
        this.blender.reset();
        this.secondaryFacialBones = { jaw: null, tongue: null, leftCheek: null, rightCheek: null, leftEye: null, rightEye: null };
        if (!vrm) return;

        this.catalogModelExpressions(vrm);
        this.catalogSecondaryFacialBones(vrm);
        this.optimizeMToonNormals(vrm);
    }

    catalogSecondaryFacialBones(vrm) {
        if (!vrm || !vrm.scene) return;
        vrm.scene.traverse((node) => {
            if (!node.isBone || !node.name) return;
            const lower = node.name.toLowerCase();
            if (lower.includes('jaw') || node.name.includes('あご') || node.name.includes('顎')) {
                this.secondaryFacialBones.jaw = node;
            } else if (lower.includes('tongue') || node.name.includes('舌')) {
                this.secondaryFacialBones.tongue = node;
            } else if (lower.includes('cheek') && (lower.includes('l') || node.name.includes('左'))) {
                this.secondaryFacialBones.leftCheek = node;
            } else if (lower.includes('cheek') && (lower.includes('r') || node.name.includes('右'))) {
                this.secondaryFacialBones.rightCheek = node;
            } else if (lower.includes('eye') && (lower.includes('l') || node.name.includes('左目'))) {
                this.secondaryFacialBones.leftEye = node;
            } else if (lower.includes('eye') && (lower.includes('r') || node.name.includes('右目'))) {
                this.secondaryFacialBones.rightEye = node;
            }
        });
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
                'aa', 'ih', 'ou', 'ee', 'oh', 'A', 'I', 'U', 'E', 'O', 'Extra', 'shy'
            ];
            candidateNames.forEach(name => {
                try {
                    const track = expMgr.getExpression ? expMgr.getExpression(name) : null;
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
        const factor = Math.max(0.0, Math.min(1.0, Number(intensity) || 0.0));
        this.blender.setEmotion(name, factor, 0.32);

        const customPreset = this.asymmetricPresets[name];
        if (customPreset) {
            for (const [morphKey, targetVal] of Object.entries(customPreset)) {
                this.blender.setMorph(morphKey, targetVal * factor, factor >= this.snapThreshold, 0.30);
                this.targetMorphs.set(morphKey, targetVal * factor);
            }
        }

        if (name === 'shocked') {
            this.targetPupilScale = 0.82;
            this.targetSecondaryState.jawPitch = 0.18 * factor;
        } else if (name === 'smug' || name === 'cat_smile') {
            this.targetPupilScale = 1.08;
            this.targetSecondaryState.cheekPuff = 0.12 * factor;
        } else {
            this.targetPupilScale = 1.0;
            this.targetSecondaryState.jawPitch = 0.0;
        }
        this.applyCoordinatedBodyPosture(name, factor);
    }

    applyCoordinatedBodyPosture(presetName, factor = 1.0) {
        if (!this.vrm) return;
        const getBone = (bName) => {
            if (typeof this.vrm.getBone === 'function') {
                return this.vrm.getBone(bName);
            }
            if (this.vrm.humanoid) {
                return this.vrm.humanoid.getNormalizedBoneNode(bName) || this.vrm.humanoid.getRawBoneNode(bName);
            }
            return null;
        };
        const spine = getBone('spine');
        const chest = getBone('chest');
        const head = getBone('head');
        const lShoulder = getBone('leftShoulder');
        const rShoulder = getBone('rightShoulder');
        const hips = getBone('hips');

        if (presetName === 'shocked' || presetName === 'surprised') {
            if (spine) spine.rotation.x -= 0.06 * factor;
            if (chest) chest.rotation.x += 0.05 * factor;
            if (lShoulder) lShoulder.rotation.z -= 0.04 * factor;
            if (rShoulder) rShoulder.rotation.z += 0.04 * factor;
        } else if (presetName === 'smug' || presetName === 'dramatic_smirk') {
            if (hips) hips.rotation.z += 0.03 * factor;
            if (spine) spine.rotation.x -= 0.03 * factor;
            if (head) head.rotation.z -= 0.06 * factor;
        } else if (presetName === 'pout' || presetName === 'embarrassed') {
            if (spine) spine.rotation.x += 0.04 * factor;
            if (head) head.rotation.x += 0.05 * factor;
            if (lShoulder) lShoulder.rotation.z += 0.03 * factor;
            if (rShoulder) rShoulder.rotation.z -= 0.03 * factor;
        }
    }

    setMorph(name, weight, snap = false) {
        const target = Math.max(0.0, Math.min(1.0, Number(weight) || 0.0));
        this.targetMorphs.set(name, target);
        this.blender.setMorph(name, target, snap, 0.30);

        if (snap) {
            this.currentMorphs.set(name, target);
            this._applyRawMorph(name, target);
        }
    }

    setViseme(name, weight) {
        this.blender.setViseme(name, weight);
    }

    resetMorphs() {
        this.targetMorphs.forEach((_, key) => {
            this.targetMorphs.set(key, 0.0);
        });
        this.blender.reset();
    }

    setDecoupledGaze(x, y, instant = false) {
        const clampX = Math.max(-0.6, Math.min(0.6, Number(x) || 0.0));
        const clampY = Math.max(-0.4, Math.min(0.4, Number(y) || 0.0));
        this.targetPupilOffset.set(clampX, clampY);
        this.blender.setDecoupledGaze(clampX, clampY, instant);

        if (instant) {
            this.leftPupilOffset.copy(this.targetPupilOffset);
            this.rightPupilOffset.copy(this.targetPupilOffset);
        }
    }

    update(dt) {
        if (!this.enabled || !this.vrm) return;

        const safeDt = Math.max(0.001, Math.min(0.05, dt));
        this.blender.update(safeDt);

        const offsets = this.blender.getSecondaryBoneOffsets();

        this.leftPupilOffset.lerp(offsets.pupilOffset, Math.min(1.0, safeDt * 24.0));
        this.rightPupilOffset.lerp(offsets.pupilOffset, Math.min(1.0, safeDt * 24.0));
        this.pupilScale = THREE.MathUtils.damp(this.pupilScale, offsets.pupilScale, 10.0, safeDt);

        if (this.secondaryFacialBones.jaw) {
            this.secondaryFacialBones.jaw.rotation.x = offsets.jawPitch;
            if (this.secondaryFacialBones.jaw.position) {
                this.secondaryFacialBones.jaw.position.z = offsets.jawForward;
            }
        }
        if (this.secondaryFacialBones.leftCheek && this.secondaryFacialBones.leftCheek.scale) {
            this.secondaryFacialBones.leftCheek.scale.setScalar(offsets.leftCheekScale);
        }
        if (this.secondaryFacialBones.rightCheek && this.secondaryFacialBones.rightCheek.scale) {
            this.secondaryFacialBones.rightCheek.scale.setScalar(offsets.rightCheekScale);
        }
        if (this.secondaryFacialBones.leftEye && this.secondaryFacialBones.leftEye.scale) {
            this.secondaryFacialBones.leftEye.scale.setScalar(this.pupilScale);
        }
        if (this.secondaryFacialBones.rightEye && this.secondaryFacialBones.rightEye.scale) {
            this.secondaryFacialBones.rightEye.scale.setScalar(this.pupilScale);
        }

        const getBone = (bName) => {
            if (typeof this.vrm.getBone === 'function') {
                return this.vrm.getBone(bName);
            }
            if (this.vrm.humanoid) {
                return this.vrm.humanoid.getNormalizedBoneNode(bName) || this.vrm.humanoid.getRawBoneNode(bName);
            }
            return null;
        };

        const neck = getBone('neck');
        const head = getBone('head');
        if (neck) {
            neck.rotation.x = THREE.MathUtils.damp(neck.rotation.x, offsets.neckPitch, 8.0, safeDt);
            neck.rotation.y = THREE.MathUtils.damp(neck.rotation.y, offsets.neckYaw, 8.0, safeDt);
            neck.rotation.z = THREE.MathUtils.damp(neck.rotation.z, offsets.neckRoll, 8.0, safeDt);
        }
        if (head) {
            head.rotation.x = THREE.MathUtils.damp(head.rotation.x, offsets.headPitch, 8.0, safeDt);
            head.rotation.y = THREE.MathUtils.damp(head.rotation.y, offsets.headYaw, 8.0, safeDt);
            head.rotation.z = THREE.MathUtils.damp(head.rotation.z, offsets.headRoll, 8.0, safeDt);
        }

        this.microTimer += safeDt;
        this.microBrowOffset = Math.sin(this.microTimer * 0.8) * 0.04;
        this.microSmileOffset = Math.max(0.0, Math.sin(this.microTimer * 0.4) * 0.06);

        const computed = this.blender.getComputedMorphs();
        computed.forEach((val, morphName) => {
            let finalVal = val;
            if (morphName === 'happy' || morphName === 'joy') {
                finalVal = Math.min(1.0, finalVal + this.microSmileOffset);
            }
            this.currentMorphs.set(morphName, finalVal);
            this._applyRawMorph(morphName, finalVal);
        });

        this.targetMorphs.forEach((targetWeight, morphName) => {
            if (!computed.has(morphName)) {
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

        if (typeof this.vrm.setExpression === 'function') {
            try {
                this.vrm.setExpression(name, clampedWeight);
                applied = true;
            } catch (e) {}
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
