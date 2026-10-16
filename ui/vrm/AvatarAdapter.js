import * as THREE from 'three';
import { VRMUtils, VRMExpressionPresetName } from '@pixiv/three-vrm';

export const MMD_MORPH_MAP = {
  joy: ['笑顔', 'にこり', '笑い', 'ウィンク２', 'にっこり', 'にひひ', 'Happy', 'Joy'],
  blink: ['まばたき', 'まばたき2', 'ウィンク', 'Blink'],
  blinkLeft: ['ウィンク', 'ウインク', 'ウィンク２', 'Blink_L'],
  blinkRight: ['ウィンク右', 'ウインク右', 'ｳｨﾝｸ２右', 'Blink_R'],
  surprised: ['びっくり', '驚き', '瞳小', 'びっくり_2', 'Surprised'],
  angry: ['怒り', '怒り2', '怒り２', '真面目', '上', 'Angry'],
  sad: ['困る', '困る2', '悲しい', '泣き', '下', 'Sad'],
  shy: ['照れ', 'テレ', '赤面', 'チーク', 'Blush'],
  smug: ['じと目', 'ジト目', 'にやり', 'Smug'],
  relaxed: ['なごみ', '穏やか', 'Relaxed'],
  aa: ['あ', 'あ＿2', 'A'],
  ih: ['い', 'いー', 'I'],
  ou: ['う', 'U'],
  ee: ['え', 'えー', 'E'],
  oh: ['お', 'おお', 'O']
};

export const MMD_BONE_MAP = {
  root: ['全ての親', '操作中心', 'Bip001', 'Root', 'root'],
  hips: ['下半身', 'センター', 'グルーブ', '腰', '腰キャンセル左', '腰キャンセル右', 'Bip001 Pelvis', 'Bip001_Pelvis', 'Pelvis', 'Hips', 'waist', 'root_pelvis'],
  spine: ['上半身', '脊椎', 'Bip001 Spine', 'Bip001_Spine', 'Spine', 'spine1', 'spine_01'],
  chest: ['上半身2', '胸', 'Bip001 Spine1', 'Bip001_Spine1', 'Chest', 'spine2', 'spine_02'],
  upperChest: ['上半身3', 'Bip001 Spine2', 'Bip001_Spine2', 'UpperChest', 'spine3'],
  neck: ['首', '脖子', 'Bip001 Neck', 'Bip001_Neck', 'Neck', 'c_neck'],
  head: ['頭', '头', 'Bip001 Head', 'Bip001_Head', 'Head', 'c_head'],
  leftEye: ['左目', 'Eye_L', 'Bip001 L Eye'],
  rightEye: ['右目', 'Eye_R', 'Bip001 R Eye'],
  jaw: ['あご', '顎', 'Jaw', 'Bip001 Jaw'],
  tongue: ['舌', '舌1', 'Tongue', 'Bip001 Tongue'],
  leftCheek: ['左頬', 'Cheek_L'],
  rightCheek: ['右頬', 'Cheek_R'],
  leftShoulder: ['左肩', '左肩P', '左肩C', '肩_L', 'Bip001 L Clavicle', 'Bip001_L_Clavicle', 'Shoulder_L', 'L_Shoulder', 'shoulder.l', 'clavicle.l'],
  rightShoulder: ['右肩', '右肩P', '右肩C', '肩_R', 'Bip001 R Clavicle', 'Bip001_R_Clavicle', 'Shoulder_R', 'R_Shoulder', 'shoulder.r', 'clavicle.r'],
  leftUpperArm: ['左腕', '左腕捩', '左腕捩1', '左上臂', '左臂', '腕_L', 'Bip001 L UpperArm', 'Bip001_L_UpperArm', 'UpperArm_L', 'L_UpperArm', 'Arm_L', 'L_Arm', 'arm.l', 'upper_arm.l'],
  rightUpperArm: ['右腕', '右腕捩', '右腕捩1', '右上臂', '右臂', '腕_R', 'Bip001 R UpperArm', 'Bip001_R_UpperArm', 'UpperArm_R', 'R_UpperArm', 'Arm_R', 'R_Arm', 'arm.r', 'upper_arm.r'],
  leftLowerArm: ['左ひじ', '左肘', '左前臂', '左手捩', '左手捩1', 'ひじ_L', 'Bip001 L Forearm', 'Bip001_L_Forearm', 'LowerArm_L', 'L_LowerArm', 'Forearm_L', 'L_Forearm', 'Elbow_L', 'L_Elbow', 'forearm.l', 'elbow.l'],
  rightLowerArm: ['右ひじ', '右肘', '右前臂', '右手捩', '右手捩1', 'ひじ_R', 'Bip001 R Forearm', 'Bip001_R_Forearm', 'LowerArm_R', 'R_LowerArm', 'Forearm_R', 'R_Forearm', 'Elbow_R', 'R_Elbow', 'forearm.r', 'elbow.r'],
  leftHand: ['左手首', '左手', '左手腕', '手首_L', 'Bip001 L Hand', 'Bip001_L_Hand', 'Hand_L', 'L_Hand', 'Wrist_L', 'L_Wrist', 'hand.l', 'wrist.l'],
  rightHand: ['右手首', '右手', '右手腕', '手首_R', 'Bip001 R Hand', 'Bip001_R_Hand', 'Hand_R', 'R_Hand', 'Wrist_R', 'R_Wrist', 'hand.r', 'wrist.r'],
  leftUpperLeg: ['左足', '左足D', '左腿', '左大腿', '足_L', 'Bip001 L Thigh', 'Bip001_L_Thigh', 'UpperLeg_L', 'L_UpperLeg', 'Thigh_L', 'L_Thigh', 'Leg_L', 'thigh.l', 'upper_leg.l'],
  rightUpperLeg: ['右足', '右足D', '右腿', '右大腿', '足_R', 'Bip001 R Thigh', 'Bip001_R_Thigh', 'UpperLeg_R', 'R_UpperLeg', 'Thigh_R', 'R_Thigh', 'Leg_R', 'thigh.r', 'upper_leg.r'],
  leftLowerLeg: ['左ひざ', '左ひざD', '左ひざ補助', '左膝', '左小腿', 'ひざ_L', 'Bip001 L Calf', 'Bip001_L_Calf', 'LowerLeg_L', 'L_LowerLeg', 'Calf_L', 'L_Calf', 'Knee_L', 'L_Knee', 'calf.l', 'knee.l'],
  rightLowerLeg: ['右ひざ', '右ひざD', '右ひざ補助', '右膝', '右小腿', 'ひざ_R', 'Bip001 R Calf', 'Bip001_R_Calf', 'LowerLeg_R', 'R_LowerLeg', 'Calf_R', 'R_Calf', 'Knee_R', 'R_Knee', 'calf.r', 'knee.r'],
  leftFoot: ['左足首', '左足首D', '左脚踝', '左踝', '足首_L', 'Bip001 L Foot', 'Bip001_L_Foot', 'Foot_L', 'L_Foot', 'Ankle_L', 'L_Ankle', 'foot.l', 'ankle.l'],
  rightFoot: ['右足首', '右足首D', '右脚踝', '右踝', '足首_R', 'Bip001 R Foot', 'Bip001_R_Foot', 'Foot_R', 'R_Foot', 'Ankle_R', 'R_Ankle', 'foot.r', 'ankle.r'],
  leftToes: ['左つま先', '左足先EX', '左脚趾', 'つま先_L', 'Bip001 L Toe0', 'Bip001_L_Toe0', 'Toes_L', 'L_Toe', 'toe.l'],
  rightToes: ['右つま先', '右足先EX', '右脚趾', 'つま先_R', 'Bip001 R Toe0', 'Bip001_R_Toe0', 'Toes_R', 'R_Toe', 'toe.r'],
  leftThumbProximal: ['左親指１', 'Bip001 L Finger0', 'Thumb1_L'],
  leftIndexProximal: ['左人指１', 'Bip001 L Finger1', 'Index1_L'],
  leftMiddleProximal: ['左中指１', 'Bip001 L Finger2', 'Middle1_L'],
  leftRingProximal: ['左薬指１', 'Bip001 L Finger3', 'Ring1_L'],
  leftLittleProximal: ['左小指１', 'Bip001 L Finger4', 'Little1_L'],
  rightThumbProximal: ['右親指１', 'Bip001 R Finger0', 'Thumb1_R'],
  rightIndexProximal: ['右人指１', 'Bip001 R Finger1', 'Index1_R'],
  rightMiddleProximal: ['右中指１', 'Bip001 R Finger2', 'Middle1_R'],
  rightRingProximal: ['右薬指１', 'Bip001 R Finger3', 'Ring1_R'],
  rightLittleProximal: ['右小指１', 'Bip001 R Finger4', 'Little1_R']
};

export const ZZZ_CHARACTER_KEYS = [
  'anby_demara', 'burnice_white', 'ellen_joe', 'hoshimi_miyabi',
  'jane_doe', 'nicole_demara', 'belle_proxy', 'billy_kid'
];

export function detectArchitectureProfile(modelPath = '') {
  const lower = String(modelPath || '').toLowerCase();
  for (const zzzKey of ZZZ_CHARACTER_KEYS) {
    const shortKey = zzzKey.split('_')[0];
    if (lower.includes(zzzKey) || lower.includes(shortKey)) {
      return 'ZZZAvatarProfile';
    }
  }
  if (lower.endsWith('.pmx') || lower.endsWith('.pmd')) {
    return 'StandardMMDProfile';
  }
  return 'VRMProfile';
}

export function NaturalBindPoseFix(target) {
  if (!target) return false;
  const getBoneNode = (name) => {
    if (typeof target.getBone === 'function') {
      return target.getBone(name);
    }
    if (target.humanoid) {
      return target.humanoid.getNormalizedBoneNode(name) || target.humanoid.getRawBoneNode(name);
    }
    return null;
  };

  const lShoulder = getBoneNode('leftShoulder');
  const rShoulder = getBoneNode('rightShoulder');
  const lUpperArm = getBoneNode('leftUpperArm');
  const rUpperArm = getBoneNode('rightUpperArm');
  const lLowerArm = getBoneNode('leftLowerArm');
  const rLowerArm = getBoneNode('rightLowerArm');
  const lUpperLeg = getBoneNode('leftUpperLeg');
  const rUpperLeg = getBoneNode('rightUpperLeg');
  const lLowerLeg = getBoneNode('leftLowerLeg');
  const rLowerLeg = getBoneNode('rightLowerLeg');

  if (lShoulder) lShoulder.rotation.set(0.02, 0.0, -0.05);
  if (rShoulder) rShoulder.rotation.set(0.02, 0.0, 0.05);

  const enforceArmDown = (upperArm, lowerArm, isLeft) => {
    if (!upperArm) return;
    if (upperArm.parent) upperArm.parent.updateWorldMatrix(true, false);
    upperArm.updateWorldMatrix(true, false);
    let needLower = true;
    if (lowerArm) {
      lowerArm.updateWorldMatrix(true, false);
      const posU = new THREE.Vector3();
      const posL = new THREE.Vector3();
      upperArm.getWorldPosition(posU);
      lowerArm.getWorldPosition(posL);
      const dir = posL.sub(posU).normalize();
      const angle = dir.angleTo(new THREE.Vector3(0, -1, 0));
      if (angle < 0.38) {
        needLower = false;
      }
    }
    if (needLower) {
      const zRot = isLeft ? -0.72 : 0.72;
      upperArm.rotation.set(0.10, isLeft ? 0.04 : -0.04, zRot);
      if (lowerArm) {
        lowerArm.rotation.set(0.20, 0.0, isLeft ? 0.12 : -0.12);
      }
    }
  };

  enforceArmDown(lUpperArm, lLowerArm, true);
  enforceArmDown(rUpperArm, rLowerArm, false);

  if (lUpperLeg) lUpperLeg.rotation.set(-0.02, 0.0, -0.02);
  if (rUpperLeg) rUpperLeg.rotation.set(-0.02, 0.0, 0.02);
  if (lLowerLeg) lLowerLeg.rotation.set(0.05, 0.0, 0.0);
  if (rLowerLeg) rLowerLeg.rotation.set(0.05, 0.0, 0.0);

  const fingersL = ['leftThumbProximal', 'leftIndexProximal', 'leftMiddleProximal', 'leftRingProximal', 'leftLittleProximal'];
  const fingersR = ['rightThumbProximal', 'rightIndexProximal', 'rightMiddleProximal', 'rightRingProximal', 'rightLittleProximal'];
  fingersL.forEach((fn) => {
    const b = getBoneNode(fn);
    if (b) b.rotation.z = -0.10;
  });
  fingersR.forEach((fn) => {
    const b = getBoneNode(fn);
    if (b) b.rotation.z = 0.10;
  });

  if (target.modelRoot && typeof target.modelRoot.updateMatrixWorld === 'function') {
    target.modelRoot.updateMatrixWorld(true);
  } else if (target.scene && typeof target.scene.updateMatrixWorld === 'function') {
    target.scene.updateMatrixWorld(true);
  }
  return true;
}

export const NaturalPostureInitializer = NaturalBindPoseFix;

export class VRMARetargeter {
  static applyNormalizedQuaternionBridge(sourceQuat, canonicalBone, isMmd = false) {
    if (!sourceQuat) return new THREE.Quaternion();
    const q = sourceQuat.clone().normalize();
    if (!isMmd) return q;
    const euler = new THREE.Euler().setFromQuaternion(q, 'YXZ');
    if (canonicalBone === 'leftUpperArm') {
      euler.z = Math.min(-0.15, euler.z - 0.35);
    } else if (canonicalBone === 'rightUpperArm') {
      euler.z = Math.max(0.15, euler.z + 0.35);
    } else if (canonicalBone === 'spine' || canonicalBone === 'chest') {
      euler.x *= 0.85;
      euler.y *= 0.90;
    }
    return new THREE.Quaternion().setFromEuler(euler).normalize();
  }

  static retargetClipToAvatar(clip, avatar) {
    if (!clip || !clip.tracks || !avatar) return clip;
    const isMmd = avatar.type === 'pmx' || Boolean(avatar.vrm && avatar.vrm.isMmd);
    const remappedTracks = [];

    for (const track of clip.tracks) {
      const dotIdx = track.name.indexOf('.');
      if (dotIdx < 0) {
        remappedTracks.push(track);
        continue;
      }
      const nodeName = track.name.slice(0, dotIdx);
      const propName = track.name.slice(dotIdx + 1);
      let targetBone = avatar.getBone(nodeName);
      if (!targetBone) {
        for (const canonical of Object.keys(MMD_BONE_MAP)) {
          if (nodeName.toLowerCase().includes(canonical.toLowerCase())) {
            targetBone = avatar.getBone(canonical);
            break;
          }
        }
      }
      if (!targetBone) {
        remappedTracks.push(track);
        continue;
      }
      if (propName === 'quaternion' && isMmd && track.values && track.values.length >= 4) {
        const newValues = new Float32Array(track.values.length);
        const tmpQ = new THREE.Quaternion();
        for (let i = 0; i < track.values.length; i += 4) {
          tmpQ.set(track.values[i], track.values[i + 1], track.values[i + 2], track.values[i + 3]).normalize();
          tmpQ.toArray(newValues, i);
        }
        remappedTracks.push(new THREE.QuaternionKeyframeTrack(`${targetBone.name}.quaternion`, track.times.slice(), newValues));
      } else {
        remappedTracks.push(track);
      }
    }
    return new THREE.AnimationClip(clip.name, clip.duration, remappedTracks);
  }
}

export class ZZZAvatarProfile {
  constructor(avatar) {
    this.name = 'ZZZAvatarProfile';
    this.avatar = avatar;
    this.springStiffness = 210.0;
    this.springDamping = 14.5;
    this.squashStretchIntensity = 1.0;
    this.rimLightIntensity = 1.35;
  }
}

export class StandardMMDProfile {
  constructor(avatar) {
    this.name = 'StandardMMDProfile';
    this.avatar = avatar;
    this.springStiffness = 145.0;
    this.springDamping = 18.0;
    this.squashStretchIntensity = 0.35;
    this.rimLightIntensity = 0.95;
  }
}

export class VRMProfile {
  constructor(avatar) {
    this.name = 'VRMProfile';
    this.avatar = avatar;
    this.springStiffness = 160.0;
    this.springDamping = 16.5;
    this.squashStretchIntensity = 0.55;
    this.rimLightIntensity = 1.05;
  }
}

export class BaseAvatar {
  constructor(modelRoot, modelPath = '') {
    this.modelRoot = modelRoot;
    this.modelPath = modelPath;
    this.type = 'base';
    this.profileType = detectArchitectureProfile(modelPath);
    this.profile = this._createProfile();
  }

  _createProfile() {
    if (this.profileType === 'ZZZAvatarProfile') return new ZZZAvatarProfile(this);
    if (this.profileType === 'StandardMMDProfile') return new StandardMMDProfile(this);
    return new VRMProfile(this);
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
  constructor(vrm, modelPath = '') {
    super(vrm.scene, modelPath);
    this.vrm = vrm;
    this.type = 'vrm';
    this.canonicalPresets = {
      joy: VRMExpressionPresetName.Happy,
      happy: VRMExpressionPresetName.Happy,
      blink: VRMExpressionPresetName.Blink,
      blinkLeft: VRMExpressionPresetName.BlinkLeft,
      blinkRight: VRMExpressionPresetName.BlinkRight,
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
    NaturalBindPoseFix(this);
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
  constructor(mesh, helper = null, modelPath = '') {
    super(mesh, modelPath);
    this.mesh = mesh;
    this.helper = helper;
    this.type = 'pmx';
    if (this.profileType === 'VRMProfile') {
      this.profileType = 'StandardMMDProfile';
      this.profile = new StandardMMDProfile(this);
    }
    this.morphIndices = new Map();
    this.boneMap = new Map();
    this.targetMorphWeights = new Map();
    this._initMorphMap();
    this._initBoneMap();
    this._applyToonWarmShading(mesh);
    NaturalBindPoseFix(this);
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
        this.boneMap.set(node.name.toLowerCase(), node);
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
          if (mat.map) {
            if (mat.color) mat.color.setRGB(1.0, 1.0, 1.0);
          } else {
            if (!mat.color) mat.color = new THREE.Color(0xf5e6dc);
          }
          if (mat.emissive) {
            mat.emissive.setRGB(0.018, 0.015, 0.012);
          }
          mat.shininess = Math.min(6.0, mat.shininess || 6.0);
          mat.roughness = this.profileType === 'ZZZAvatarProfile' ? 0.35 : 0.42;
          mat.metalness = this.profileType === 'ZZZAvatarProfile' ? 0.08 : 0.02;
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
      let idx = this.morphIndices.get(jaName);
      if (idx === undefined) idx = this.morphIndices.get(jaName.toLowerCase());
      if (idx !== undefined) {
        this.targetMorphWeights.set(idx, w);
        return;
      }
    }
  }

  setViseme(visemeName, weight) {
    this.setExpression(visemeName, weight);
  }

  getBone(canonicalBoneName) {
    const candidates = MMD_BONE_MAP[canonicalBoneName];
    const searchList = Array.isArray(candidates) ? candidates : [candidates || canonicalBoneName];
    for (const candidate of searchList) {
      if (this.boneMap.has(candidate)) {
        return this.boneMap.get(candidate);
      }
      const cLow = String(candidate).toLowerCase();
      if (this.boneMap.has(cLow)) {
        return this.boneMap.get(cLow);
      }
    }
    for (const [k, b] of this.boneMap.entries()) {
      for (const candidate of searchList) {
        const cStr = String(candidate).toLowerCase();
        if (k.toLowerCase().includes(cStr)) {
          return b;
        }
      }
    }
    if (this.mesh && this.mesh.skeleton && this.mesh.skeleton.bones) {
      const bones = this.mesh.skeleton.bones;
      const isL = canonicalBoneName.toLowerCase().includes('left');
      const isR = canonicalBoneName.toLowerCase().includes('right');
      const isArm = canonicalBoneName.toLowerCase().includes('arm');
      const isLeg = canonicalBoneName.toLowerCase().includes('leg');
      if (isArm) {
        for (const b of bones) {
          const bn = b.name.toLowerCase();
          if ((bn.includes('arm') || bn.includes('腕') || bn.includes('肩')) && !bn.includes('twist') && !bn.includes('捩')) {
            if (isL && (bn.includes('l') || bn.includes('左'))) return b;
            if (isR && (bn.includes('r') || bn.includes('右'))) return b;
          }
        }
      }
      if (isLeg) {
        for (const b of bones) {
          const bn = b.name.toLowerCase();
          if ((bn.includes('leg') || bn.includes('thigh') || bn.includes('足') || bn.includes('腿')) && !bn.includes('ik')) {
            if (isL && (bn.includes('l') || bn.includes('左'))) return b;
            if (isR && (bn.includes('r') || bn.includes('右'))) return b;
          }
        }
      }
    }
    return null;
  }

  update(deltaTime) {
    const dt = Math.max(0.001, Math.min(0.05, Number(deltaTime) || 0.016));
    if (this.helper) {
      this.helper.update(dt);
    }
    if (this.mesh && this.mesh.morphTargetInfluences && this.targetMorphWeights.size > 0) {
      const factor = Math.min(1.0, dt * 18.0);
      this.targetMorphWeights.forEach((targetW, idx) => {
        const cur = this.mesh.morphTargetInfluences[idx] || 0.0;
        if (Math.abs(cur - targetW) > 0.002) {
          this.mesh.morphTargetInfluences[idx] = THREE.MathUtils.lerp(cur, targetW, factor);
        } else {
          this.mesh.morphTargetInfluences[idx] = targetW;
        }
      });
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
          const adapter = new MMDAvatar(mesh, loaders.mmdHelper || null, path);
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
          const adapter = new VRMAvatar(vrm, path);
          resolve(adapter);
        },
        options.onProgress,
        (err) => reject(err)
      );
    });
  }
}
