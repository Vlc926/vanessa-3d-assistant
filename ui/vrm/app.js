import * as THREE from 'three';
window.THREE = THREE;
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils, VRMExpressionPresetName } from '@pixiv/three-vrm';
import { VRMAnimationLoaderPlugin } from '@pixiv/three-vrm-animation';
import { AnimationController } from './animation_controller.js?v=20261012_v4';
import { GazeController } from './gaze_controller.js?v=20261012_v4';
import { MOTION_DEFINITIONS } from './personality_kinematics.js?v=20261012_v4';
import { FootIKSolver } from './foot_ik_solver.js?v=20261012_v4';
import { MotionMatchingEngine } from './motion_matching.js?v=20261012_v4';
import { AnimeFXRenderer } from './anime_fx_renderer.js';
import { ChibiMorphModifier } from './chibi_morph_modifier.js';
import { HierarchicalEmotionEngine } from './hierarchical_emotion_engine.js';
import { SensoryPerceptionBroker } from './sensory_perception_broker.js';
import { SquashAndStretchModifier } from './squash_stretch_modifier.js?v=20261012_v4';
import { FrameModulationController } from './frame_modulation_controller.js?v=20261012_v4';
import { AnimeFacialDriver } from './anime_facial_driver.js?v=20261012_v4';
import { SpringDynamicsTuner } from './spring_dynamics_tuner.js?v=20261012_v4';
import { ConsciousSkeletalDriver } from './conscious_skeletal_driver.js?v=20261012_v4';
import { GachaCinematicController } from './gacha_cinematic_controller.js?v=20261012_v4';
import { MMDHumanoidAdapter } from './mmd_humanoid_adapter.js?v=20261012_v5';
import { GachaAnimationGraph } from './gacha_animation_graph.js?v=20261012_v5';
import { DedicatedPMXController } from './dedicated_pmx_controller.js?v=20261012_v5';

import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import { MMDLoader } from 'three/addons/loaders/MMDLoader.js';
import { TGALoader } from 'three/addons/loaders/TGALoader.js';
import { AnimationEngine, SmartLocomotionRouter } from './AnimationEngine.js';
import { VRMAvatar, MMDAvatar, loadAvatarModel, detectArchitectureProfile, NaturalBindPoseFix } from './AvatarAdapter.js';

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, window.innerWidth / window.innerHeight, 0.1, 20.0);
camera.position.set(0, 0.75, 2.8);

const renderer = new THREE.WebGLRenderer({
    alpha: true,
    antialias: true,
    powerPreference: 'high-performance',
    preserveDrawingBuffer: true
});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2.5));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.18;
document.body.appendChild(renderer.domElement);

const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
scene.add(ambientLight);
const dirLight = new THREE.DirectionalLight(0xffffff, 1.25);
dirLight.position.set(1.2, 2.6, 2.2);
scene.add(dirLight);
const fillLight = new THREE.DirectionalLight(0xeef4ff, 0.65);
fillLight.position.set(-1.2, 0.8, 1.5);
scene.add(fillLight);
const rimLight = new THREE.DirectionalLight(0xfff0f6, 0.95);
rimLight.position.set(-1.2, 2.5, -2.0);
scene.add(rimLight);

const loader = new GLTFLoader();
loader.register((parser) => new VRMLoaderPlugin(parser));
loader.register((parser) => new VRMAnimationLoaderPlugin(parser));
const fbxLoader = new FBXLoader();
const mmdLoadingManager = new THREE.LoadingManager();
mmdLoadingManager.addHandler(/\.tga$/i, new TGALoader());
const mmdLoader = new MMDLoader(mmdLoadingManager);

const animController = new AnimationController(loader);
const gazeController = new GazeController(scene);
const footIkSolver = new FootIKSolver();
const motionMatching = new MotionMatchingEngine(animController, footIkSolver);
const animeFxRenderer = new AnimeFXRenderer(scene);
const chibiModifier = new ChibiMorphModifier();
const squashStretchModifier = new SquashAndStretchModifier();
const frameModulationController = new FrameModulationController();
const animeFacialDriver = new AnimeFacialDriver();
const springDynamicsTuner = new SpringDynamicsTuner();
const consciousSkeletalDriver = new ConsciousSkeletalDriver();
const gachaCinematicController = new GachaCinematicController();
const mmdHumanoidAdapter = new MMDHumanoidAdapter();
const gachaAnimationGraph = new GachaAnimationGraph();
const dedicatedPmxController = new DedicatedPMXController();
const emotionEngine = new HierarchicalEmotionEngine(animController, animeFxRenderer, chibiModifier);
const sensoryBroker = new SensoryPerceptionBroker(gazeController, emotionEngine, animeFxRenderer, chibiModifier);

let currentVrm = null;
let currentExternalMesh = null;
let currentAvatarAdapter = null;
const animationEngine = new AnimationEngine();
animationEngine.setFacialDriver(animeFacialDriver);
let directiveSocket = null;
let directiveReconnectTimer = null;
let avatarMode = 'standard';
let targetScaleFactor = 1.0;
let currentScaleFactor = 1.0;
let baseModelScale = 1.0;
let isThrottled = false;
let throttleFps = 15.0;
let lastRenderTime = 0.0;
let clock = new THREE.Clock();
let pythonBridge = null;
let currentBodyYaw = 0.0;
let targetBodyYaw = 0.0;
let bodyYawSpeed = 5.0;
const vrmBufferCache = new Map();

animController.onExpressionRequested = (expr, weight) => {
    setExpression(expr, weight);
};
motionMatching.onExpressionTrigger = (expr, weight) => {
    setExpression(expr, weight);
};

export function setMorphTarget(name, weight = 1.0) {
    if (!currentVrm || !currentVrm.scene) return;
    const w = Math.max(0, Math.min(1, Number(weight) || 0));
    currentVrm.scene.traverse((node) => {
        if (node.isMesh && node.morphTargetDictionary && node.morphTargetInfluences) {
            if (name in node.morphTargetDictionary) {
                const idx = node.morphTargetDictionary[name];
                node.morphTargetInfluences[idx] = w;
            } else {
                for (const key of Object.keys(node.morphTargetDictionary)) {
                    if (key.toLowerCase() === name.toLowerCase()) {
                        const idx = node.morphTargetDictionary[key];
                        node.morphTargetInfluences[idx] = w;
                        break;
                    }
                }
            }
        }
    });
}

export function setExpression(name, weight = 1.0) {
    if (!currentVrm) return;
    const lower = (name || 'neutral').toLowerCase();
    const w = Math.max(0, Math.min(1, Number(weight) || 0));

    if (animeFacialDriver) {
        animeFacialDriver.setAsymmetricPreset(lower, w);
    }

    if (currentVrm.isMmd && dedicatedPmxController) {
        dedicatedPmxController.setExpression(lower, w);
    }

    if (currentVrm.expressionManager) {
        const presets = [
            VRMExpressionPresetName.Happy,
            VRMExpressionPresetName.Sad,
            VRMExpressionPresetName.Angry,
            VRMExpressionPresetName.Surprised,
            VRMExpressionPresetName.Relaxed,
            VRMExpressionPresetName.Neutral
        ];
        presets.forEach(p => {
            try { currentVrm.expressionManager.setValue(p, 0.0); } catch (e) {}
        });
    }

    const resetMorphs = [
        'mouthSmileLeft', 'mouthSmileRight', 'cheekSquintLeft', 'cheekSquintRight',
        'browInnerUp', 'browDownLeft', 'browDownRight', 'mouthFrownLeft', 'mouthFrownRight',
        'eyeWideLeft', 'eyeWideRight', 'jawOpen', '_mouthPress+CatMouth',
        'Fcl_ALL_Joy', 'Fcl_ALL_Sorrow', 'Fcl_ALL_Angry', 'Fcl_EYE_Surprised', 'Fcl_BRW_Angry', 'Fcl_EYE_Sorrow'
    ];
    resetMorphs.forEach(m => setMorphTarget(m, 0.0));

    if (lower === 'happy') {
        if (currentVrm.expressionManager) currentVrm.expressionManager.setValue(VRMExpressionPresetName.Happy, w * 0.9);
        setMorphTarget('mouthSmileLeft', w * 0.85);
        setMorphTarget('mouthSmileRight', w * 0.85);
        setMorphTarget('cheekSquintLeft', w * 0.5);
        setMorphTarget('cheekSquintRight', w * 0.5);
        setMorphTarget('browInnerUp', w * 0.3);
        setMorphTarget('Fcl_ALL_Joy', w * 0.85);
    } else if (lower === 'pout') {
        if (currentVrm.expressionManager) currentVrm.expressionManager.setValue(VRMExpressionPresetName.Angry, w * 0.5);
        setMorphTarget('browDownLeft', w * 0.7);
        setMorphTarget('browDownRight', w * 0.7);
        setMorphTarget('mouthFrownLeft', w * 0.6);
        setMorphTarget('mouthFrownRight', w * 0.6);
        setMorphTarget('Fcl_BRW_Angry', w * 0.8);
    } else if (lower === 'cat_face' || lower === 'nya') {
        if (currentVrm.expressionManager) currentVrm.expressionManager.setValue(VRMExpressionPresetName.Happy, w * 0.7);
        setMorphTarget('mouthSmileLeft', w * 0.8);
        setMorphTarget('mouthSmileRight', w * 0.8);
        setMorphTarget('_mouthPress+CatMouth', w * 0.6);
        setMorphTarget('cheekSquintLeft', w * 0.5);
        setMorphTarget('cheekSquintRight', w * 0.5);
    } else if (lower === 'star_eyes') {
        if (currentVrm.expressionManager) currentVrm.expressionManager.setValue(VRMExpressionPresetName.Surprised, w * 0.6);
        setMorphTarget('eyeWideLeft', w * 0.85);
        setMorphTarget('eyeWideRight', w * 0.85);
        setMorphTarget('mouthSmileLeft', w * 0.75);
        setMorphTarget('mouthSmileRight', w * 0.75);
        setMorphTarget('browInnerUp', w * 0.6);
        setMorphTarget('Fcl_ALL_Joy', w * 0.7);
    } else if (lower === 'flustered' || lower === 'blush') {
        if (currentVrm.expressionManager) currentVrm.expressionManager.setValue(VRMExpressionPresetName.Relaxed, w * 0.6);
        setMorphTarget('mouthSmileLeft', w * 0.5);
        setMorphTarget('mouthSmileRight', w * 0.5);
        setMorphTarget('cheekSquintLeft', w * 0.8);
        setMorphTarget('cheekSquintRight', w * 0.8);
        setMorphTarget('browInnerUp', w * 0.4);
    } else if (lower === 'smug') {
        if (currentVrm.expressionManager) currentVrm.expressionManager.setValue(VRMExpressionPresetName.Happy, w * 0.4);
        setMorphTarget('mouthSmileRight', w * 0.85);
        setMorphTarget('cheekSquintRight', w * 0.5);
        setMorphTarget('browDownLeft', w * 0.4);
        setMorphTarget('browInnerUp', w * 0.4);
    } else if (lower === 'caring' || lower === 'relaxed') {
        if (currentVrm.expressionManager) currentVrm.expressionManager.setValue(VRMExpressionPresetName.Relaxed, w * 0.8);
        setMorphTarget('mouthSmileLeft', w * 0.55);
        setMorphTarget('mouthSmileRight', w * 0.55);
        setMorphTarget('browInnerUp', w * 0.3);
    } else if (lower === 'surprised' || lower === 'shock') {
        if (currentVrm.expressionManager) currentVrm.expressionManager.setValue(VRMExpressionPresetName.Surprised, w * 0.9);
        setMorphTarget('eyeWideLeft', w * 0.9);
        setMorphTarget('eyeWideRight', w * 0.9);
        setMorphTarget('jawOpen', w * 0.4);
        setMorphTarget('browInnerUp', w * 0.8);
        setMorphTarget('Fcl_EYE_Surprised', w * 0.9);
    } else if (lower === 'sad' || lower === 'crying_chibi') {
        if (currentVrm.expressionManager) currentVrm.expressionManager.setValue(VRMExpressionPresetName.Sad, w * 0.9);
        setMorphTarget('mouthFrownLeft', w * 0.7);
        setMorphTarget('mouthFrownRight', w * 0.7);
        setMorphTarget('browInnerUp', w * 0.75);
        setMorphTarget('Fcl_ALL_Sorrow', w * 0.85);
    } else if (lower === 'winking_kawaii' || lower === 'wink') {
        if (currentVrm.expressionManager) {
            currentVrm.expressionManager.setValue(VRMExpressionPresetName.BlinkLeft, w * 1.0);
            currentVrm.expressionManager.setValue(VRMExpressionPresetName.Happy, w * 0.7);
        }
        setMorphTarget('mouthSmileLeft', w * 0.8);
        setMorphTarget('mouthSmileRight', w * 0.8);
        setMorphTarget('cheekSquintRight', w * 0.6);
        setTimeout(() => {
            if (currentVrm && currentVrm.expressionManager) {
                try { currentVrm.expressionManager.setValue(VRMExpressionPresetName.BlinkLeft, 0.0); } catch (e) {}
            }
        }, 1200);
    } else if (lower === 'thinking') {
        setMorphTarget('browInnerUp', w * 0.35);
        setMorphTarget('browDownLeft', w * 0.25);
    } else if (lower === 'curious') {
        setMorphTarget('eyeWideLeft', w * 0.5);
        setMorphTarget('eyeWideRight', w * 0.5);
        setMorphTarget('mouthSmileLeft', w * 0.4);
        setMorphTarget('mouthSmileRight', w * 0.4);
        setMorphTarget('browInnerUp', w * 0.4);
    } else {
        if (currentVrm.expressionManager) currentVrm.expressionManager.setValue(VRMExpressionPresetName.Neutral, w * 1.0);
    }
}

export function setMouth(ratio) {
    if (!currentVrm || !currentVrm.expressionManager) return;
    const clamped = Math.max(0.0, Math.min(1.0, Number(ratio) || 0));
    try {
        currentVrm.expressionManager.setValue(VRMExpressionPresetName.Aa, clamped);
    } catch (e) {}
}

export function updateVisemeLipSync(ratio) {
    setMouth(ratio);
}

export function resetLipSync() {
    setMouth(0.0);
}

export function playMotion(name) {
    return animController.playMotion(name);
}

export function setWalkSpeed(speedRatio) {
    animController.setWalkSpeed(speedRatio);
}

export function setBodyFacing(relativeYawRadians, turnSpeed = 5.0) {
    const clampedRel = Math.max(-0.45, Math.min(0.45, Number(relativeYawRadians) || 0.0));
    targetBodyYaw = 0.0 + clampedRel;
    bodyYawSpeed = turnSpeed;
    if (motionMatching) {
        motionMatching.targetYaw = targetBodyYaw;
        motionMatching.turnSpeed = turnSpeed;
    }
}

export function lookAt(x, y) {
    gazeController.lookAt(x, y);
}

export function playNextStandbyPose() {
    const stands = ['idle_loop', 'relax'];
    const pick = stands[Math.floor(Math.random() * stands.length)];
    animController.setStandby(pick);
    animController.playMotion(pick, 0.45);
}

export function playNextPlayfulMotion() {
    const playful = [
        'cat_pose', 'heart_hands', 'peace', 'clapping', 'thinking',
        'bow', 'wave', 'look_around', 'model_pose',
        'cheeks_kawaii', 'fidget_shy', 'pout_shake'
    ];
    const pick = playful[Math.floor(Math.random() * playful.length)];
    animController.playMotion(pick, 0.40);
}

export function startWalking(dir = 1, speed = 1.0) {
    if (dedicatedPmxController) {
        dedicatedPmxController.startWalking(speed);
    }
    animController.setWalkSpeed(speed);
    animController.playMotion('walk');
}

export function stopWalking() {
    if (dedicatedPmxController) {
        dedicatedPmxController.stopWalking();
    }
    animController.playMotion('idle_loop');
}

export function setPersonaMood(mood) {
    const m = (mood || 'calm').toLowerCase();
    if (m === 'schwi') animController.setStandby('idle_loop');
    else if (m === 'amadeus') animController.setStandby('relax');
    else if (m === 'isla') animController.setStandby('idle_loop');
    else animController.setStandby('idle_loop');
}

function frameAvatar(vrm) {
    if (!vrm || !vrm.scene) return;
    const box = new THREE.Box3().setFromObject(vrm.scene);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const vFovRad = (camera.fov * Math.PI) / 180;
    const hFovRad = 2 * Math.atan(Math.tan(vFovRad / 2) * camera.aspect);
    const distY = (size.y * 1.36) / (2 * Math.tan(vFovRad / 2));
    const distX = (size.x * 1.32) / (2 * Math.tan(hFovRad / 2));
    const dist = Math.max(distY, distX, 2.7);
    const targetY = center.y + size.y * 0.03;
    camera.position.set(0, targetY, dist);
    camera.lookAt(0, targetY, 0);
}

function disposeVRM(vrm) {
    if (!vrm || !vrm.scene) return;
    try {
        vrm.scene.traverse((node) => {
            if (node.geometry) node.geometry.dispose();
            if (node.material) {
                const mats = Array.isArray(node.material) ? node.material : [node.material];
                for (const m of mats) {
                    for (const key in m) {
                        const val = m[key];
                        if (val && typeof val === 'object' && val.isTexture) val.dispose();
                    }
                    m.dispose();
                }
            }
        });
        VRMUtils.deepDispose(vrm.scene);
    } catch (e) {}
}

export function setAvatarMode(mode = 'standard') {
    avatarMode = 'standard';
    targetScaleFactor = 1.0;
}

export function setThrottling(throttled = false, targetFps = 15.0) {
    isThrottled = Boolean(throttled);
    throttleFps = Math.max(1.0, Math.min(60.0, Number(targetFps) || 15.0));
}

export const ZZZHybridToonShader = {
    applyToRoot(root, isZZZ = true) {
        if (!root) return;
        rimLight.intensity = isZZZ ? 1.42 : 0.95;
        root.traverse((child) => {
            if (child.isMesh && child.material) {
                const mats = Array.isArray(child.material) ? child.material : [child.material];
                mats.forEach((mat) => {
                    const matName = String(mat.name || child.name || '').toLowerCase();
                    const isSkinOrFace = matName.includes('skin') || matName.includes('face') || matName.includes('body') || matName.includes('肌') || matName.includes('顔');
                    const isMetalOrLeather = matName.includes('metal') || matName.includes('leather') || matName.includes('cloth') || matName.includes('jacket') || matName.includes('weapon');
                    if (isZZZ) {
                        if (isSkinOrFace) {
                            mat.roughness = 0.85;
                            mat.metalness = 0.01;
                            if (mat.emissive) mat.emissive.setRGB(0.032, 0.020, 0.018);
                        } else if (isMetalOrLeather) {
                            mat.roughness = 0.20;
                            mat.metalness = 0.38;
                            if (mat.emissive) mat.emissive.setRGB(0.018, 0.022, 0.030);
                        } else {
                            mat.roughness = 0.26;
                            mat.metalness = 0.14;
                        }
                    } else if (mat.isMeshStandardMaterial || mat.isMeshPhysicalMaterial) {
                        mat.roughness = Math.max(0.65, mat.roughness);
                        mat.metalness = Math.min(0.08, mat.metalness);
                    }
                });
            }
        });
    }
};

function applyCelShading(root, profileName = 'VRMProfile') {
    if (!root) return;
    ZZZHybridToonShader.applyToRoot(root, profileName === 'ZZZAvatarProfile');
}

let activeArchitectureProfile = 'VRMProfile';

function updateHudProfileTabs(profileName) {
    activeArchitectureProfile = profileName;
    document.querySelectorAll('[data-profile]').forEach((btn) => {
        if (btn.getAttribute('data-profile') === profileName) {
            btn.style.borderColor = '#38bdf8';
            btn.style.color = '#38bdf8';
        } else {
            btn.style.borderColor = 'rgba(255, 255, 255, 0.12)';
            btn.style.color = '#f8fafc';
        }
    });
}

function disposeMesh(mesh) {
    if (!mesh) return;
    mesh.traverse((node) => {
        if (node.geometry) node.geometry.dispose();
        if (node.material) {
            const mats = Array.isArray(node.material) ? node.material : [node.material];
            mats.forEach((m) => {
                for (const key in m) {
                    const val = m[key];
                    if (val && typeof val === 'object' && val.isTexture) val.dispose();
                }
                m.dispose();
            });
        }
    });
}

let activityState = 'standby';
let lastActivityTime = performance.now();

export function notifyActivity(state = 'action') {
    lastActivityTime = performance.now();
    activityState = state;
}

let isModelTransitioning = false;

function triggerHologramTransition(start = true) {
    const overlay = document.getElementById('fortnite-hologram-overlay');
    if (!overlay) return;
    if (start) {
        overlay.classList.add('active');
    } else {
        setTimeout(() => {
            overlay.classList.remove('active');
        }, 320);
    }
}

export function setModel(path) {
    if (!path) return;
    notifyActivity('action');
    triggerHologramTransition(true);
    const detectedProfile = detectArchitectureProfile(path);
    updateHudProfileTabs(detectedProfile);
    const modelSelector = document.getElementById('model-selector');
    if (modelSelector && modelSelector.value !== path) {
        modelSelector.value = path;
    }
    const lower = path.toLowerCase();
    const onLoaded = (gltf) => {
        const newVrm = gltf.userData ? gltf.userData.vrm : null;
        if (!newVrm) {
            triggerHologramTransition(false);
            return;
        }
        VRMUtils.removeUnnecessaryVertices(newVrm.scene);
        VRMUtils.removeUnnecessaryJoints(newVrm.scene);
        if (currentVrm) {
            scene.remove(currentVrm.scene);
            disposeVRM(currentVrm);
            currentVrm = null;
        }
        if (currentExternalMesh) {
            scene.remove(currentExternalMesh);
            disposeMesh(currentExternalMesh);
            currentExternalMesh = null;
        }

        scene.add(newVrm.scene);
        currentVrm = newVrm;
        NaturalBindPoseFix(newVrm);
        currentAvatarAdapter = new VRMAvatar(newVrm, path);
        animationEngine.setAvatar(currentAvatarAdapter);
        baseModelScale = 1.0;
        newVrm.scene.scale.set(baseModelScale * currentScaleFactor, baseModelScale * currentScaleFactor, baseModelScale * currentScaleFactor);
        newVrm.scene.rotation.y = Math.PI;
        applyCelShading(newVrm.scene, detectedProfile);
        animController.setVrm(newVrm, currentAvatarAdapter);
        footIkSolver.setVrm(newVrm);
        animeFxRenderer.setVrm(newVrm);
        chibiModifier.setVrm(newVrm);
        squashStretchModifier.setVrm(newVrm);
        frameModulationController.setVrm(newVrm);
        animeFacialDriver.setVrm(newVrm);
        springDynamicsTuner.setVrm(newVrm);
        consciousSkeletalDriver.setVrm(newVrm);
        gachaCinematicController.setVrm(newVrm);
        gachaAnimationGraph.setVrm(newVrm, path);
        frameAvatar(newVrm);
        animController.playMotion('idle_loop');
        const urls = Object.values(MOTION_DEFINITIONS).map(d => d.file);
        animController.preloadClips(urls);
        triggerHologramTransition(false);
        if (pythonBridge && pythonBridge.on_avatar_ready) {
            pythonBridge.on_avatar_ready();
        }
    };

    if (lower.endsWith('.fbx')) {
        fbxLoader.load(path, (fbx) => {
            if (currentVrm) {
                scene.remove(currentVrm.scene);
                disposeVRM(currentVrm);
                currentVrm = null;
            }
            if (currentExternalMesh) {
                scene.remove(currentExternalMesh);
                disposeMesh(currentExternalMesh);
            }
            baseModelScale = 0.01;
            fbx.scale.setScalar(baseModelScale * currentScaleFactor);
            applyCelShading(fbx, detectedProfile);
            scene.add(fbx);
            currentExternalMesh = fbx;
            triggerHologramTransition(false);
        });
    } else if (lower.endsWith('.pmx') || lower.endsWith('.pmd')) {
        mmdLoader.load(
            path,
            (mmd) => {
                if (currentVrm) {
                    scene.remove(currentVrm.scene);
                    disposeVRM(currentVrm);
                    currentVrm = null;
                }
                if (currentExternalMesh) {
                    scene.remove(currentExternalMesh);
                    disposeMesh(currentExternalMesh);
                }
                scene.add(mmd);
                currentExternalMesh = mmd;
                currentAvatarAdapter = new MMDAvatar(mmd, null, path);
                animationEngine.setAvatar(currentAvatarAdapter);
                const adapted = mmdHumanoidAdapter.adaptModel(mmd);
                if (adapted) {
                    currentVrm = adapted;
                    NaturalBindPoseFix(adapted);
                    dedicatedPmxController.applyModelCalibration(path, mmd, adapted, camera);
                    applyCelShading(mmd, detectedProfile);
                    animController.setVrm(adapted, currentAvatarAdapter);
                    footIkSolver.setVrm(adapted);
                    animeFxRenderer.setVrm(adapted);
                    squashStretchModifier.setVrm(adapted);
                    animeFacialDriver.setVrm(adapted);
                }
                triggerHologramTransition(false);
                if (pythonBridge && pythonBridge.on_avatar_ready) {
                    pythonBridge.on_avatar_ready();
                }
            },
            undefined,
            (err) => {
                console.error('[MMDLoader] Failed to load PMX:', err);
                triggerHologramTransition(false);
                if (!currentVrm && !currentExternalMesh) {
                    setModel('/ui/static/vrm_models/Vanessa_Flagship_Anime.vrm');
                }
            }
        );
    } else {
        if (vrmBufferCache.has(path)) {
            const buf = vrmBufferCache.get(path).slice(0);
            loader.parse(buf, '', onLoaded, () => {
                loader.load(path, onLoaded);
            });
        } else {
            fetch(path)
                .then(r => r.arrayBuffer())
                .then(buf => {
                    vrmBufferCache.set(path, buf);
                    loader.parse(buf.slice(0), '', onLoaded, () => {
                        loader.load(path, onLoaded);
                    });
                })
                .catch(() => {
                    loader.load(path, onLoaded);
                });
        }
    }
}

function checkResize() {
    const w = window.innerWidth || 440;
    const h = window.innerHeight || 750;
    if (w > 0 && h > 0) {
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
        if (currentVrm && !currentVrm.isMmd) {
            frameAvatar(currentVrm);
        } else if (currentVrm && currentVrm.isMmd && dedicatedPmxController) {
            dedicatedPmxController.frameCamera(currentExternalMesh, camera);
        }
    }
}
window.addEventListener('resize', checkResize);
window.addEventListener('wheel', (e) => e.preventDefault(), { passive: false });
window.addEventListener('gesturestart', (e) => e.preventDefault());
window.addEventListener('gesturechange', (e) => e.preventDefault());
window.addEventListener('gestureend', (e) => e.preventDefault());
document.addEventListener('wheel', (e) => e.preventDefault(), { passive: false });

function animate() {
    requestAnimationFrame(animate);
    if (document.hidden) return;

    const now = performance.now();
    if (activityState === 'action' && (now - lastActivityTime > 4000)) {
        activityState = 'standby';
    }

    let targetFps = 60.0;
    if (isThrottled || activityState === 'sleep') {
        targetFps = throttleFps;
    } else {
        targetFps = 60.0;
    }

    const minDelta = 1000.0 / targetFps;
    if (now - lastRenderTime < minDelta) return;
    lastRenderTime = now;

    const dt = Math.min(0.045, clock.getDelta());

    if (!currentVrm || !currentVrm.isMmd) {
        if (Math.abs(currentScaleFactor - targetScaleFactor) > 0.001) {
            currentScaleFactor += (targetScaleFactor - currentScaleFactor) * Math.min(1.0, dt * 10.0);
            const finalScale = baseModelScale * currentScaleFactor;
            if (currentVrm && currentVrm.scene) {
                currentVrm.scene.scale.set(finalScale, finalScale, finalScale);
            }
            if (currentExternalMesh) {
                currentExternalMesh.scale.set(finalScale, finalScale, finalScale);
            }
        }
    }

    if (currentVrm) {
        sensoryBroker.update(dt);
        if (!currentVrm.isMmd) {
            chibiModifier.update(dt);
            animeFxRenderer.update(dt);
            motionMatching.update(dt, currentVrm);
            animController.update(dt);
            gazeController.update(dt, currentVrm);
            springDynamicsTuner.update(dt);
            currentVrm.update(dt);
            frameModulationController.update(dt);
            squashStretchModifier.update(dt);
            animeFacialDriver.update(dt);
            footIkSolver.update(dt);
            consciousSkeletalDriver.update(dt);
            gachaCinematicController.update(dt);
            gachaAnimationGraph.setLocomotion(motionMatching.isLocomoting, motionMatching.currentSpeed, motionMatching.targetYaw, motionMatching.facingYaw);
            gachaAnimationGraph.update(dt);
        } else {
            animController.update(dt);
            dedicatedPmxController.updateProceduralDynamics(dt, currentVrm);
            animeFacialDriver.update(dt);
            squashStretchModifier.update(dt);
            footIkSolver.update(dt);
            animeFxRenderer.update(dt);
        }
        if (currentVrm.scene) {
            const baseRot = Math.PI;
            const rotOffset = (currentVrm && currentVrm.isMmd) ? -Math.PI : 0.0;
            const yaw = currentVrm.isMmd ? 0.0 : motionMatching.facingYaw;
            currentVrm.scene.rotation.y = baseRot + rotOffset + yaw;
        }
    }
    animationEngine.update(dt);
    if (currentAvatarAdapter) {
        currentAvatarAdapter.update(dt);
    }
    renderer.render(scene, camera);
}

window.vrmController = {
    animationEngine,
    getAvatarAdapter: () => currentAvatarAdapter,
    setDirective: (dir) => {
        animationEngine.setDirective(dir);
        if (dir && dir.state) updateHudStateBadge(dir.state);
    },
    animController,
    motionMatching,
    dedicatedPmxController,
    setExpression,
    setMouth,
    updateVisemeLipSync,
    resetLipSync,
    setMorphTarget,
    setAvatarMode,
    setThrottling,
    notifyActivity,
    consciousSkeletalDriver,
    gachaCinematicController,
    gachaAnimationGraph,
    mmdHumanoidAdapter,
    applyConsciousSkeletalPacket: (packet) => {
        if (!packet) return;
        notifyActivity('action');
        consciousSkeletalDriver.applyPacket(packet);
        if (packet.channel1_conversation) {
            gachaAnimationGraph.handleConversationTurn(packet.channel1_conversation.role, packet.channel1_conversation.intent, packet.channel1_conversation.emotion);
        }
        if (packet.channel6_tactical) {
            gachaCinematicController.setCombatStance(packet.channel6_tactical.active);
        }
        if (packet.biomechanical_pose && packet.biomechanical_pose.facial_preset) {
            animeFacialDriver.setAsymmetricPreset(packet.biomechanical_pose.facial_preset, packet.biomechanical_pose.facial_intensity || 1.0);
        }
    },
    applyCanonicalCommandPacket: (packet) => {
        if (!packet) return;
        notifyActivity('action');
        consciousSkeletalDriver.applyPacket(packet);
        if (packet.action) {
            if (currentVrm && currentVrm.isMmd && dedicatedPmxController) {
                dedicatedPmxController.triggerGesture(packet.action, 3.0);
            }
            motionMatching.receiveMotorCommand(packet.action, 0, 0, 0, packet.emotion ? packet.emotion.mood : null, 'standby');
        }
        if (packet.emotion && packet.emotion.mood) {
            setExpression(packet.emotion.mood, packet.emotion.intensity || 1.0);
        }
        if (packet.avatar_mode) {
            setAvatarMode(packet.avatar_mode);
        }
        if (packet.blendshapes_weights) {
            for (const [key, val] of Object.entries(packet.blendshapes_weights)) {
                if (val > 0.05) setMorphTarget(key, val);
            }
        }
        if (packet.facial_preset) {
            animeFacialDriver.setAsymmetricPreset(packet.facial_preset, packet.facial_intensity || 1.0);
        }
        if (packet.squash_stretch) {
            squashStretchModifier.applyImpulse(packet.squash_stretch.bone, packet.squash_stretch.factor);
        }
        if (packet.anime_fps) {
            frameModulationController.setAnimeFps(packet.anime_fps);
        }
        if (packet.spring_profile) {
            springDynamicsTuner.setProfile(packet.spring_profile);
        }
    },
    receiveMotorCommand: (intent, vx, vy, speed, mood, posture) => {
        notifyActivity('action');
        if (currentVrm && currentVrm.isMmd && dedicatedPmxController && intent) {
            dedicatedPmxController.triggerGesture(intent, 3.0);
        }
        motionMatching.receiveMotorCommand(intent, vx, vy, speed, mood, posture);
    },
    playMotion: (name) => {
        notifyActivity('action');
        if (currentVrm && currentVrm.isMmd && dedicatedPmxController) {
            dedicatedPmxController.triggerGesture(name, 3.0);
        }
        motionMatching.receiveMotorCommand(name, 0, 0, 0, null, 'standby');
    },
    playGesture: (name, duration = 3.0) => {
        notifyActivity('action');
        if (currentVrm && currentVrm.isMmd && dedicatedPmxController) {
            dedicatedPmxController.triggerGesture(name, duration);
        }
        motionMatching.receiveMotorCommand(name, 0, 0, 0, null, 'standby');
    },
    setWalkSpeed: (speed) => {
        animController.setWalkSpeed(speed);
        motionMatching.targetSpeed = Number(speed) || 1.0;
    },
    setBodyFacing: (relativeYawRadians, turnSpeed = 5.0) => {
        setBodyFacing(relativeYawRadians, turnSpeed);
    },
    playNextStandbyPose: () => {
        notifyActivity('action');
        playNextStandbyPose();
    },
    playNextPlayfulMotion: () => {
        notifyActivity('action');
        playNextPlayfulMotion();
    },
    lookAt,
    setModel,
    frameAvatar: () => {
        if (!currentVrm) return;
        if (currentVrm.isMmd && dedicatedPmxController && currentExternalMesh) {
            dedicatedPmxController.frameCamera(currentExternalMesh, camera);
        } else if (currentVrm.scene) {
            frameAvatar(currentVrm);
        }
    },
    startWalking: (dir = 1, speed = 1.0) => {
        notifyActivity('action');
        if (dedicatedPmxController) {
            dedicatedPmxController.startWalking(speed);
        }
        motionMatching.receiveMotorCommand('walk', dir, 0, speed, null, 'locomotion');
    },
    stopWalking: () => {
        notifyActivity('action');
        if (dedicatedPmxController) {
            dedicatedPmxController.stopWalking();
        }
        motionMatching.receiveMotorCommand('idle', 0, 0, 0, null, 'standby');
    },
    setPersonaMood,
    setPerched: (perched, perchStyle = 'sit') => {
        notifyActivity('action');
        motionMatching.setPerched(perched, perchStyle);
    },
    setReadingMode: (reading) => {
        motionMatching.setReadingMode(reading);
    },
    setMusicActive: (active, bpm = 120.0) => {
        notifyActivity('action');
        if (dedicatedPmxController) {
            dedicatedPmxController.setMusicActive(active, bpm);
        }
    },
    setMusicGenre: (genre = 'pop', bpm = 120.0) => {
        notifyActivity('action');
        if (dedicatedPmxController) {
            dedicatedPmxController.setMusicGenre(genre, bpm);
        }
    },
    onSensoryEvent: (payload) => {
        notifyActivity('action');
        sensoryBroker.processEvent(payload);
    },
    triggerAnimeFX: (type, options) => {
        notifyActivity('action');
        animeFxRenderer.trigger(type, options);
    },
    setChibiMode: (enable) => {
        notifyActivity('action');
        setAvatarMode('standard');
    },
    squashStretchModifier,
    frameModulationController,
    animeFacialDriver,
    springDynamicsTuner,
    setAsymmetricFacialPreset: (preset, intensity = 1.0) => {
        notifyActivity('action');
        animeFacialDriver.setAsymmetricPreset(preset, intensity);
    },
    triggerSquash: (intensity = 1.0) => {
        notifyActivity('action');
        squashStretchModifier.triggerSquash(intensity);
    },
    triggerStretch: (intensity = 1.0) => {
        notifyActivity('action');
        squashStretchModifier.triggerStretch(intensity);
    },
    setAnimeFps: (fps) => {
        frameModulationController.setAnimeFps(fps);
    },
    setSpringProfile: (profile) => {
        springDynamicsTuner.setProfile(profile);
    },
    applyExternalPhysicsImpulse: (dx, dy, dt) => {
        springDynamicsTuner.applyExternalImpulse(dx, dy, dt);
    },
    syncLocomotionStep: (vx = 0.0, vy = 0.0, stridePhase = 0.0) => {
        footIkSolver.syncLocomotionStep(vx, vy, stridePhase);
        animationEngine.syncLocomotionStep(vx, vy, stridePhase, 0, 0);
    },
    setPhysicalState: (state, options = {}) => {
        notifyActivity('action');
        animationEngine.setPhysicalState(state, options);
        if (state === 'PERCHED') {
            const style = options.style || 'sit';
            footIkSolver.setPerched(true, style);
            motionMatching.setPerched(true, style);
        } else if (state === 'FREE_FALL') {
            footIkSolver.setPerched(false);
            motionMatching.setPerched(false);
            springDynamicsTuner.applyExternalImpulse(0.0, -Math.abs(options.vy || 250.0) * 0.05, 0.016);
        } else if (state === 'DRAGGED_IN_AIR') {
            footIkSolver.setPerched(false);
            motionMatching.setPerched(false);
        } else {
            footIkSolver.setPerched(false);
            motionMatching.setPerched(false);
            if (options.landingCompression) {
                footIkSolver.triggerLandingCompression(options.landingCompression);
                squashStretchModifier.triggerSquash(options.landingCompression);
            }
        }
    },
    triggerHeadpat: (active = true, cursorX = 0.0) => {
        notifyActivity('action');
        animationEngine.triggerHeadpat(active, cursorX);
        if (active) {
            animeFacialDriver.setAsymmetricPreset('relaxed', 0.95);
            animeFxRenderer.trigger('sparkle', { duration: 1.5 });
        }
    },
    triggerWindowClosePanic: (active = true) => {
        notifyActivity('action');
        animationEngine.triggerWindowClosePanic(active);
        if (active) {
            animeFacialDriver.setAsymmetricPreset('panic', 1.0);
            animeFxRenderer.trigger('exclamation', { duration: 1.4 });
        }
    },
    setVerticalPostureOffset: (crouchDepth = 0.0, tiptoeHeight = 0.0) => {
        footIkSolver.setVerticalPostureOffset(crouchDepth, tiptoeHeight);
    },
    switchArchitectureProfile: (profileName) => {
        if (currentAvatarAdapter && typeof currentAvatarAdapter.setProfile === 'function') {
            currentAvatarAdapter.setProfile(profileName);
            updateHudProfileTabs(profileName);
        }
    }
};

function persistLearnedBehavior(behavior) {
    if (!behavior) return;
    if (directiveSocket && directiveSocket.readyState === WebSocket.OPEN) {
        try {
            directiveSocket.send(JSON.stringify({
                type: 'save_learned_behavior',
                behavior
            }));
        } catch (e) {}
    }
}

animationEngine.onSaveLearnedBehavior = persistLearnedBehavior;
animeFacialDriver.onLearnedBehaviorSynthesized = persistLearnedBehavior;

function initWebChannel() {
    if (typeof QWebChannel !== 'undefined' && window.qt && window.qt.webChannelTransport) {
        new QWebChannel(qt.webChannelTransport, (channel) => {
            pythonBridge = channel.objects.vrmBridge;
            animController.setBridge(pythonBridge);
            console.log('[VRM] QWebChannel connected to Python bridge!');
        });
    }
}

function updateHudStateBadge(state) {
    const badge = document.getElementById('directive-state-badge');
    if (!badge) return;
    const st = String(state || 'IDLE').toUpperCase();
    badge.textContent = st;
    badge.className = 'state-badge';
    if (st === 'LISTENING') {
        badge.classList.add('state-listening');
    } else if (st === 'THINKING') {
        badge.classList.add('state-thinking');
    } else if (st === 'SPEAKING') {
        badge.classList.add('state-speaking');
    } else {
        badge.classList.add('state-idle');
    }
}

function initDirectiveSocket(port = 8765) {
    if (directiveSocket && (directiveSocket.readyState === WebSocket.OPEN || directiveSocket.readyState === WebSocket.CONNECTING)) {
        return;
    }
    try {
        directiveSocket = new WebSocket(`ws://127.0.0.1:${port}`);
        directiveSocket.onopen = () => {};
        directiveSocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'avatar_directive') {
                    if (data.state) {
                        updateHudStateBadge(data.state);
                    }
                    animationEngine.setDirective(data);
                    if (data.facial_preset) {
                        animeFacialDriver.setAsymmetricPreset(data.facial_preset, data.facial_intensity || 1.0);
                    } else if (data.emotion_vector) {
                        const topEmo = Object.entries(data.emotion_vector).sort((a, b) => b[1] - a[1])[0];
                        if (topEmo && topEmo[1] > 0.35) {
                            animeFacialDriver.setAsymmetricPreset(topEmo[0], topEmo[1]);
                        }
                    }
                }
            } catch (e) {}
        };
        directiveSocket.onclose = () => {
            if (directiveReconnectTimer) clearTimeout(directiveReconnectTimer);
            directiveReconnectTimer = setTimeout(() => initDirectiveSocket(port), 3000);
        };
        directiveSocket.onerror = () => {
            try { directiveSocket.close(); } catch (e) {}
        };
    } catch (e) {
        if (directiveReconnectTimer) clearTimeout(directiveReconnectTimer);
        directiveReconnectTimer = setTimeout(() => initDirectiveSocket(port), 3000);
    }
}

function initHudControls() {
    const toggleBtn = document.getElementById('btn-toggle-hud');
    const hudContainer = document.getElementById('hud-container');
    if (toggleBtn && hudContainer) {
        toggleBtn.addEventListener('click', () => {
            hudContainer.classList.toggle('collapsed');
            toggleBtn.textContent = hudContainer.classList.contains('collapsed') ? '+' : '−';
        });
    }

    document.querySelectorAll('[data-profile]').forEach((tab) => {
        tab.addEventListener('click', () => {
            const prof = tab.getAttribute('data-profile');
            if (prof) {
                window.vrmController.switchArchitectureProfile(prof);
            }
        });
    });

    const modelSelector = document.getElementById('model-selector');
    if (modelSelector) {
        modelSelector.addEventListener('change', (e) => {
            if (e.target.value) {
                setModel(e.target.value);
            }
        });
    }

    const micBtn = document.getElementById('btn-mic-toggle');
    let micMuted = false;
    if (micBtn) {
        micBtn.addEventListener('click', () => {
            micMuted = !micMuted;
            if (micMuted) {
                micBtn.textContent = '🔇 Mic: OFF';
                micBtn.classList.add('muted');
            } else {
                micBtn.textContent = '🎙️ Mic: ON';
                micBtn.classList.remove('muted');
            }
            if (directiveSocket && directiveSocket.readyState === WebSocket.OPEN) {
                directiveSocket.send(JSON.stringify({ type: 'toggle_mic', muted: micMuted }));
            }
        });
    }

    document.querySelectorAll('[data-emotion]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const emo = btn.getAttribute('data-emotion');
            const vec = { joy: 0.0, curiosity: 0.0, surprise: 0.0, tension: 0.0, confidence: 0.5, shyness: 0.0 };
            if (emo === 'joy') vec.joy = 0.95;
            else if (emo === 'curiosity') vec.curiosity = 0.85;
            else if (emo === 'surprise') vec.surprise = 0.9;
            else if (emo === 'shyness') vec.shyness = 0.85;
            else if (emo === 'tension') vec.tension = 0.8;
            animationEngine.setDirective({
                state: 'SPEAKING',
                emotion_vector: vec,
                dialogue_text: emo
            });
            updateHudStateBadge('SPEAKING');
            setTimeout(() => updateHudStateBadge('IDLE'), 2500);
        });
    });

    document.querySelectorAll('[data-gesture]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const gesture = btn.getAttribute('data-gesture');
            animationEngine.playGesture(gesture, 3.2);
        });
    });
}

if (document.readyState === 'complete' || document.readyState === 'interactive') {
    initWebChannel();
    initDirectiveSocket();
    initHudControls();
} else {
    document.addEventListener('DOMContentLoaded', () => {
        initWebChannel();
        initDirectiveSocket();
        initHudControls();
    });
}

const params = new URLSearchParams(window.location.search);
const initialModel = params.get('model') || '/ui/static/vrm_models/Vanessa_Flagship_Anime.vrm';
setModel(initialModel);
animate();
