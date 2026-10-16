import * as THREE from 'three';
import { VRMUtils, VRMExpressionPresetName } from '@pixiv/three-vrm';

export const MMD_MORPH_MAP = {
  joy: ['笑顔', 'にこり', '笑い', 'ウィンク２'],
  blink: ['まばたき', 'ウィンク'],
  surprised: ['びっくり', '驚き', '瞳小'],
  angry: ['怒り', '真面目', '上'],
  sad: ['困る', '悲しい', '下'],
  shy: ['照れ', '赤面'],
  aa: ['あ'], ih: ['い'], ou: ['う'], ee: ['え'], oh: ['お']
};

export const MMD_BONE_MAP = {
  head: '頭', neck: '首', spine: '上半身', chest: '上半身2',
  hips: '下半身', leftEye: '左目', rightEye: '右目',
  leftShoulder: '左肩', rightShoulder: '右肩',
  leftUpperArm: '左腕', rightUpperArm: '右腕',
  leftLowerArm: '左ひじ', rightLowerArm: '右ひじ',
  leftHand: '左手首', rightHand: '右手首',
  leftUpperLeg: '左足', rightUpperLeg: '右足',
  leftLowerLeg: '左ひざ', rightLowerLeg: '右ひざ',
  leftFoot: '左足首', rightFoot: '右足首'
};

export class BaseAvatar {
  constructor(modelRoot) {
    this.modelRoot = modelRoot;
    this.type = 'base';
  }

  setExpression(canonicalName, weight) {}

  setViseme(visemeName, weight) {}

  getBone(canonicalBoneName) {
    return null;
  }

  update(deltaTime) {}

  dispose() {}
}

export class VRMAvatar extends BaseAvatar {
  constructor(vrm) {
    super(vrm.scene);
    this.vrm = vrm;
    this.type = 'vrm';
    this.canonicalPresets = {
      joy: VRMExpressionPresetName.Happy,
      blink: VRMExpressionPresetName.Blink,
      surprised: VRMExpressionPresetName.Surprised,
      angry: VRMExpressionPresetName.Angry,
      sad: VRMExpressionPresetName.Sad,
      relaxed: VRMExpressionPresetName.Relaxed,
      aa: VRMExpressionPresetName.Aa,
      ih: VRMExpressionPresetName.Ih,
      ou: VRMExpressionPresetName.Ou,
      ee: VRMExpressionPresetName.Ee,
      oh: VRMExpressionPresetName.Oh
    };
  }

  setExpression(canonicalName, weight) {
    if (!this.vrm || !this.vrm.expressionManager) return;
    const w = Math.max(0.0, Math.min(1.0, Number(weight) || 0.0));
    const preset = this.canonicalPresets[canonicalName] || canonicalName;
    try {
      this.vrm.expressionManager.setValue(preset, w);
    } catch (e) {
      this._fallbackMorph(canonicalName, w);
    }
  }

  setViseme(visemeName, weight) {
    if (!this.vrm || !this.vrm.expressionManager) return;
    const w = Math.max(0.0, Math.min(1.0, Number(weight) || 0.0));
    const preset = this.canonicalPresets[visemeName] || visemeName;
    try {
      this.vrm.expressionManager.setValue(preset, w);
    } catch (e) {
      this._fallbackMorph(visemeName, w);
    }
  }

  _fallbackMorph(name, weight) {
    if (!this.vrm || !this.vrm.scene) return;
    this.vrm.scene.traverse((node) => {
      if (node.isMesh && node.morphTargetDictionary && node.morphTargetInfluences) {
        if (name in node.morphTargetDictionary) {
          node.morphTargetInfluences[node.morphTargetDictionary[name]] = weight;
        }
      }
    });
  }

  getBone(canonicalBoneName) {
    if (!this.vrm || !this.vrm.humanoid) return null;
    return this.vrm.humanoid.getNormalizedBoneNode(canonicalBoneName) ||
           this.vrm.humanoid.getRawBoneNode(canonicalBoneName);
  }

  update(deltaTime) {
    if (this.vrm) {
      this.vrm.update(deltaTime);
    }
  }

  dispose() {
    if (this.vrm && this.vrm.scene) {
      VRMUtils.deepDispose(this.vrm.scene);
    }
  }
}

export class MMDAvatar extends BaseAvatar {
  constructor(mesh, helper = null) {
    super(mesh);
    this.mesh = mesh;
    this.helper = helper;
    this.type = 'pmx';
    this.morphIndices = new Map();
    this.boneMap = new Map();
    this._initMorphMap();
    this._initBoneMap();
    this._applyToonWarmShading(mesh);
  }

  _initMorphMap() {
    if (!this.mesh) return;
    const dict = this.mesh.morphTargetDictionary || {};
    for (const [key, idx] of Object.entries(dict)) {
      this.morphIndices.set(key, idx);
      this.morphIndices.set(key.toLowerCase(), idx);
    }
  }

  _initBoneMap() {
    if (!this.mesh) return;
    this.mesh.traverse((node) => {
      if (node.isBone && node.name) {
        this.boneMap.set(node.name, node);
      }
    });
  }

  _applyToonWarmShading(mesh) {
    if (!mesh) return;
    mesh.traverse((node) => {
      const nName = String(node.name || '').toLowerCase();
      if (
        nName.includes('親') ||
        nName.includes('センター') ||
        nName.includes('center') ||
        nName.includes('root') ||
        nName.includes('gizmo') ||
        nName.includes('helper') ||
        nName.includes('marker') ||
        nName.includes('anchor') ||
        nName.includes('axis') ||
        nName.includes('ik親') ||
        nName.includes('操作中心')
      ) {
        node.visible = false;
      }
      if (node.isMesh && node.material) {
        const mats = Array.isArray(node.material) ? node.material : [node.material];
        mats.forEach((mat) => {
          mat.side = THREE.DoubleSide;
          if (mat.color) {
            mat.color.setRGB(1.0, 1.0, 1.0);
          }
          if (mat.emissive) {
            mat.emissive.setRGB(0.025, 0.018, 0.015);
          }
          mat.roughness = 0.32;
          mat.metalness = 0.02;
          mat.depthWrite = true;
          mat.alphaTest = 0.05;
        });
      }
    });
  }

  setExpression(canonicalName, weight) {
    if (!this.mesh || !this.mesh.morphTargetInfluences) return;
    const w = Math.max(0.0, Math.min(1.0, Number(weight) || 0.0));
    const targetNames = MMD_MORPH_MAP[canonicalName] || [canonicalName];
    for (const jaName of targetNames) {
      if (this.morphIndices.has(jaName)) {
        const idx = this.morphIndices.get(jaName);
        this.mesh.morphTargetInfluences[idx] = w;
        return;
      }
    }
  }

  setViseme(visemeName, weight) {
    this.setExpression(visemeName, weight);
  }

  getBone(canonicalBoneName) {
    const jaName = MMD_BONE_MAP[canonicalBoneName] || canonicalBoneName;
    if (this.boneMap.has(jaName)) {
      return this.boneMap.get(jaName);
    }
    for (const [k, b] of this.boneMap.entries()) {
      if (k.includes(jaName) || k.toLowerCase().includes(canonicalBoneName.toLowerCase())) {
        return b;
      }
    }
    return null;
  }

  update(deltaTime) {
    if (this.helper) {
      this.helper.update(deltaTime);
    }
  }

  dispose() {
    if (this.mesh) {
      this.mesh.traverse((node) => {
        if (node.geometry) node.geometry.dispose();
        if (node.material) {
          const mats = Array.isArray(node.material) ? node.material : [node.material];
          mats.forEach(m => m.dispose());
        }
      });
    }
  }
}

export async function loadAvatarModel(path, loaders, scene, options = {}) {
  const lower = String(path || '').toLowerCase();
  if (lower.endsWith('.pmx') || lower.endsWith('.pmd')) {
    return new Promise((resolve, reject) => {
      loaders.mmdLoader.load(
        path,
        (mesh) => {
          const adapter = new MMDAvatar(mesh, loaders.mmdHelper || null);
          resolve(adapter);
        },
        options.onProgress,
        (err) => reject(err)
      );
    });
  } else {
    return new Promise((resolve, reject) => {
      loaders.gltfLoader.load(
        path,
        (gltf) => {
          const vrm = gltf.userData.vrm;
          if (!vrm) {
            reject(new Error('GLTF does not contain VRM'));
            return;
          }
          VRMUtils.removeUnnecessaryVertices(vrm.scene);
          VRMUtils.removeUnnecessaryJoints(vrm.scene);
          const adapter = new VRMAvatar(vrm);
          resolve(adapter);
        },
        options.onProgress,
        (err) => reject(err)
      );
    });
  }
}
