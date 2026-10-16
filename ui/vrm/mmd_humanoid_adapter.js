import * as THREE from 'three';

export class MMDHumanoidAdapter {
    constructor() {
        this.boneMap = {
            '操作中心': 'root',
            '全ての親': 'root',
            'センター': 'hips',
            'グルーブ': 'hips',
            '下半身': 'hips',
            '腰': 'hips',
            'センター先': 'hips',
            'グルーブ先': 'hips',
            '上半身': 'spine',
            '上半身2': 'chest',
            '上半身3': 'upperChest',
            '首': 'neck',
            '頭': 'head',
            '両目': 'head',
            '左肩P': 'leftShoulder',
            '右肩P': 'rightShoulder',
            '左肩': 'leftShoulder',
            '右肩': 'rightShoulder',
            '左肩C': 'leftShoulder',
            '右肩C': 'rightShoulder',
            '左腕': 'leftUpperArm',
            '右腕': 'rightUpperArm',
            '左腕捩': 'leftUpperArm',
            '右腕捩': 'rightUpperArm',
            '左ひじ': 'leftLowerArm',
            '右ひじ': 'rightLowerArm',
            '左手捩': 'leftLowerArm',
            '右手捩': 'rightLowerArm',
            '左手首': 'leftHand',
            '右手首': 'rightHand',
            '左親指０': 'leftThumbMetacarpal',
            '左親指１': 'leftThumbProximal',
            '左親指２': 'leftThumbDistal',
            '左人指１': 'leftIndexProximal',
            '左人指２': 'leftIndexIntermediate',
            '左人指３': 'leftIndexDistal',
            '左中指１': 'leftMiddleProximal',
            '左中指２': 'leftMiddleIntermediate',
            '左中指３': 'leftMiddleDistal',
            '左薬指１': 'leftRingProximal',
            '左薬指２': 'leftRingIntermediate',
            '左薬指３': 'leftRingDistal',
            '左小指１': 'leftLittleProximal',
            '左小指２': 'leftLittleIntermediate',
            '左小指３': 'leftLittleDistal',
            '右親指０': 'rightThumbMetacarpal',
            '右親指１': 'rightThumbProximal',
            '右親指２': 'rightThumbDistal',
            '右人指１': 'rightIndexProximal',
            '右人指２': 'rightIndexIntermediate',
            '右人指３': 'rightIndexDistal',
            '右中指１': 'rightMiddleProximal',
            '右中指２': 'rightMiddleIntermediate',
            '右中指３': 'rightMiddleDistal',
            '右薬指１': 'rightRingProximal',
            '右薬指２': 'rightRingIntermediate',
            '右薬指３': 'rightRingDistal',
            '右小指１': 'rightLittleProximal',
            '右小指２': 'rightLittleIntermediate',
            '右小指３': 'rightLittleDistal',
            '左足': 'leftUpperLeg',
            '右足': 'rightUpperLeg',
            '左足D': 'leftUpperLeg',
            '右足D': 'rightUpperLeg',
            '左ひざ': 'leftLowerLeg',
            '右ひざ': 'rightLowerLeg',
            '左ひざD': 'leftLowerLeg',
            '右ひざD': 'rightLowerLeg',
            '左足首': 'leftFoot',
            '右足首': 'rightFoot',
            '左足首D': 'leftFoot',
            '右足首D': 'rightFoot',
            '左つま先': 'leftToes',
            '右つま先': 'rightToes',
            '左目': 'leftEye',
            '右目': 'rightEye',
            'root': 'root',
            'hips': 'hips',
            'pelvis': 'hips',
            'waist': 'hips',
            'spine': 'spine',
            'chest': 'chest',
            'upperchest': 'upperChest',
            'neck': 'neck',
            'head': 'head',
            'leftshoulder': 'leftShoulder',
            'rightshoulder': 'rightShoulder',
            'leftupperarm': 'leftUpperArm',
            'rightupperarm': 'rightUpperArm',
            'leftlowerarm': 'leftLowerArm',
            'rightlowerarm': 'rightLowerArm',
            'lefthand': 'leftHand',
            'righthand': 'rightHand',
            'leftupperleg': 'leftUpperLeg',
            'rightupperleg': 'rightUpperLeg',
            'leftlowerleg': 'leftLowerLeg',
            'rightlowerleg': 'rightLowerLeg',
            'leftfoot': 'leftFoot',
            'rightfoot': 'rightFoot'
        };

        this.morphMap = {
            'まばたき': 'blink',
            'まばたき2': 'blink',
            'ウィンク': 'blinkLeft',
            'ウインク': 'blinkLeft',
            'ウィンク２': 'blinkLeft',
            'ウインク2': 'blinkLeft',
            'ウィンク右': 'blinkRight',
            'ウインク右': 'blinkRight',
            'ｳｨﾝｸ２右': 'blinkRight',
            'ウインク2右': 'blinkRight',
            '笑い': 'happy',
            'にこり': 'happy',
            'にっこり': 'happy',
            'にひひ': 'happy',
            '笑い目': 'happy',
            '困る': 'sad',
            '困る2': 'sad',
            '泣き': 'sad',
            '怒り': 'angry',
            '怒り2': 'angry',
            '怒り２': 'angry',
            '驚き': 'surprised',
            'びっくり': 'surprised',
            'びっくり_2': 'surprised',
            'じと目': 'smug',
            'ジト目': 'smug',
            'なごみ': 'relaxed',
            '穏やか': 'relaxed',
            'きらきら目': 'star_eyes',
            'ハート目': 'heart_eyes',
            'ハート瞳': 'heart_eyes',
            '照れ': 'blush',
            'テレ': 'blush',
            'チーク': 'blush',
            'てへぺろ': 'kawaii',
            'ぺろっ': 'kawaii',
            'あ': 'aa',
            'あ＿2': 'aa',
            'い': 'ih',
            'いー': 'ih',
            'う': 'ou',
            'え': 'ee',
            'えー': 'ee',
            'お': 'oh',
            'おお': 'oh'
        };

        this.normalizedBones = {};
        this.mesh = null;
        this.humanoid = null;
    }

    adaptModel(rootObject) {
        this.normalizedBones = {};
        this.mesh = null;

        if (!rootObject) return null;

        rootObject.traverse((node) => {
            if (node.isSkinnedMesh && !this.mesh) {
                this.mesh = node;
            }
            if (node.isBone) {
                const name = node.name;
                const mappedName = this.boneMap[name];
                if (mappedName && !this.normalizedBones[mappedName]) {
                    this.normalizedBones[mappedName] = node;
                }
                const lower = name.toLowerCase();
                for (const [key, target] of Object.entries(this.boneMap)) {
                    if (lower === key.toLowerCase() && !this.normalizedBones[target]) {
                        this.normalizedBones[target] = node;
                    }
                }
                for (const [key, target] of Object.entries(this.boneMap)) {
                    if (lower.includes(target.toLowerCase()) && !this.normalizedBones[target]) {
                        this.normalizedBones[target] = node;
                    }
                }
            }
        });

        if (!this.normalizedBones['hips']) {
            const fallbackNode = this.normalizedBones['root'] || (this.mesh && this.mesh.skeleton && this.mesh.skeleton.bones && this.mesh.skeleton.bones[0]) || rootObject;
            this.normalizedBones['hips'] = fallbackNode;
        }

        const humanBones = {};
        const normalizedRestPose = {};
        for (const [name, node] of Object.entries(this.normalizedBones)) {
            humanBones[name] = { node: node };
            normalizedRestPose[name] = {
                position: [node.position.x || 0, node.position.y || 0, node.position.z || 0]
            };
        }

        const hipsNode = this.normalizedBones['hips'];
        const restHipsY = (hipsNode && typeof hipsNode.position.y === 'number' && hipsNode.position.y > 0.001)
            ? hipsNode.position.y
            : 1.0;

        if (!normalizedRestPose.hips) {
            normalizedRestPose.hips = { position: [0, restHipsY, 0] };
        } else if (!normalizedRestPose.hips.position || normalizedRestPose.hips.position[1] <= 0.001) {
            normalizedRestPose.hips.position = [hipsNode.position.x || 0, restHipsY, hipsNode.position.z || 0];
        }

        this.humanoid = {
            humanBones: humanBones,
            normalizedRestPose: normalizedRestPose,
            getNormalizedBoneNode: (name) => this.normalizedBones[name] || null,
            getRawBoneNode: (name) => this.normalizedBones[name] || null,
            getBoneNode: (name) => this.normalizedBones[name] || null
        };

        return {
            scene: rootObject,
            humanoid: this.humanoid,
            meta: { metaVersion: '1' },
            expressionManager: this.createExpressionProxy(),
            isMmd: true,
            update: (dt) => {}
        };
    }

    isolateMmdIkChains(rootObject) {
        rootObject.traverse((node) => {
            if (node.name && (node.name.includes('ＩＫ') || node.name.includes('IK') || node.name.includes('ik'))) {
                node._isMmdIk = true;
                node.matrixAutoUpdate = false;
            }
        });
    }

    createExpressionProxy() {
        const self = this;
        return {
            getExpressionTrackName: (presetName) => null,
            setValue: (presetName, value) => {
                if (!self.mesh || !self.mesh.morphTargetDictionary || !self.mesh.morphTargetInfluences) return;
                const dict = self.mesh.morphTargetDictionary;
                const influences = self.mesh.morphTargetInfluences;

                for (const [jpName, enPreset] of Object.entries(self.morphMap)) {
                    if (enPreset === presetName && dict[jpName] !== undefined) {
                        influences[dict[jpName]] = THREE.MathUtils.clamp(value, 0.0, 1.0);
                    }
                }
                if (dict[presetName] !== undefined) {
                    influences[dict[presetName]] = THREE.MathUtils.clamp(value, 0.0, 1.0);
                }
            },
            getValue: (presetName) => {
                if (!self.mesh || !self.mesh.morphTargetDictionary || !self.mesh.morphTargetInfluences) return 0.0;
                const dict = self.mesh.morphTargetDictionary;
                const influences = self.mesh.morphTargetInfluences;
                if (dict[presetName] !== undefined) {
                    return influences[dict[presetName]];
                }
                for (const [jpName, enPreset] of Object.entries(self.morphMap)) {
                    if (enPreset === presetName && dict[jpName] !== undefined) {
                        return influences[dict[jpName]];
                    }
                }
                return 0.0;
            }
        };
    }
}
