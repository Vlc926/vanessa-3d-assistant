import * as THREE from 'three';

export const PMX_MODEL_PROFILES = {
    'burnice_white': {
        scale: 0.090,
        cameraDist: 2.75,
        targetYOffset: 0.03,
        hipsY: 1.04,
        armLeft: [0.12, 0.04, -1.22],
        armRight: [0.12, -0.04, 1.22],
        forearmLeft: [0.20, 0.0, 0.15],
        forearmRight: [0.20, 0.0, -0.15]
    },
    'ellen_joe': {
        scale: 0.088,
        cameraDist: 2.75,
        targetYOffset: 0.04,
        hipsY: 1.08,
        armLeft: [0.10, 0.05, -1.25],
        armRight: [0.10, -0.05, 1.25],
        forearmLeft: [0.18, 0.0, 0.12],
        forearmRight: [0.18, 0.0, -0.12]
    },
    'jane_doe': {
        scale: 0.087,
        cameraDist: 2.70,
        targetYOffset: 0.03,
        hipsY: 1.02,
        armLeft: [0.11, 0.04, -1.20],
        armRight: [0.11, -0.04, 1.20],
        forearmLeft: [0.22, 0.0, 0.14],
        forearmRight: [0.22, 0.0, -0.14]
    },
    'anby_demara': {
        scale: 0.086,
        cameraDist: 2.65,
        targetYOffset: 0.02,
        hipsY: 0.98,
        armLeft: [0.10, 0.05, -1.22],
        armRight: [0.10, -0.05, 1.22],
        forearmLeft: [0.19, 0.0, 0.12],
        forearmRight: [0.19, 0.0, -0.12]
    },
    'nicole_demara': {
        scale: 0.089,
        cameraDist: 2.80,
        targetYOffset: 0.04,
        hipsY: 1.06,
        armLeft: [0.13, 0.04, -1.24],
        armRight: [0.13, -0.04, 1.24],
        forearmLeft: [0.21, 0.0, 0.16],
        forearmRight: [0.21, 0.0, -0.16]
    },
    'hoshimi_miyabi': {
        scale: 0.088,
        cameraDist: 2.75,
        targetYOffset: 0.03,
        hipsY: 1.03,
        armLeft: [0.10, 0.05, -1.23],
        armRight: [0.10, -0.05, 1.23],
        forearmLeft: [0.18, 0.0, 0.13],
        forearmRight: [0.18, 0.0, -0.13]
    },
    'hoshimachi_suisei': {
        scale: 0.086,
        cameraDist: 2.75,
        targetYOffset: 0.03,
        hipsY: 1.05,
        armLeft: [0.12, 0.04, -1.22],
        armRight: [0.12, -0.04, 1.22],
        forearmLeft: [0.20, 0.0, 0.15],
        forearmRight: [0.20, 0.0, -0.15],
        swaySpeed: 1.25,
        swayAmp: 0.035,
        headTilt: 0.075,
        breathSpeed: 2.3,
        specialMorphs: { happy: '笑い', wink: 'ウィンク', surprised: 'びっくり', smile: 'にこり', smug: 'じと目', curious: 'びっくり', thinking: '困惑', doubt: '困惑' }
    },
    'houshou_marine': {
        scale: 0.088,
        cameraDist: 2.75,
        targetYOffset: 0.03,
        hipsY: 1.02,
        armLeft: [0.10, 0.05, -1.24],
        armRight: [0.10, -0.05, 1.24],
        forearmLeft: [0.18, 0.0, 0.12],
        forearmRight: [0.18, 0.0, -0.12],
        swaySpeed: 1.45,
        swayAmp: 0.048,
        headTilt: 0.090,
        breathSpeed: 2.5,
        specialMorphs: { happy: 'にこり', wink: 'ウィンク', angry: '怒り', pout: '怒り２', shy: '照れ', curious: 'じと目', thinking: '困る', surprised: 'びっくり', doubt: '困る' }
    },
    'inugami_korone': {
        scale: 0.090,
        cameraDist: 2.70,
        targetYOffset: 0.02,
        hipsY: 0.98,
        armLeft: [0.11, 0.04, -1.20],
        armRight: [0.11, -0.04, 1.20],
        forearmLeft: [0.20, 0.0, 0.14],
        forearmRight: [0.20, 0.0, -0.14],
        swaySpeed: 1.70,
        swayAmp: 0.052,
        headTilt: 0.110,
        breathSpeed: 2.8,
        specialMorphs: { happy: '笑い', wink: 'ウィンク', excited: 'きらきら目', heart: 'ハート目', cute: 'てへぺろ', nya: '▲', curious: 'びっくり', thinking: 'なごみ', surprised: 'びっくり', doubt: 'なごみ' }
    },
    'nekomata_okayu': {
        scale: 0.088,
        cameraDist: 2.75,
        targetYOffset: 0.03,
        hipsY: 1.03,
        armLeft: [0.10, 0.04, -1.22],
        armRight: [0.10, -0.04, 1.22],
        forearmLeft: [0.19, 0.0, 0.13],
        forearmRight: [0.19, 0.0, -0.13],
        swaySpeed: 0.95,
        swayAmp: 0.026,
        headTilt: 0.055,
        breathSpeed: 1.8,
        specialMorphs: { happy: '笑い', relaxed: 'なごみ', smirk: 'にやり', cute: 'ω', smug: 'じと目', cat: 'にっこり', curious: 'じと目', thinking: '困り', surprised: 'びっくり', doubt: '困り' }
    },
    'tsunomaki_watame': {
        scale: 0.089,
        cameraDist: 2.70,
        targetYOffset: 0.02,
        hipsY: 1.00,
        armLeft: [0.12, 0.04, -1.22],
        armRight: [0.12, -0.04, 1.22],
        forearmLeft: [0.18, 0.0, 0.12],
        forearmRight: [0.18, 0.0, -0.12],
        swaySpeed: 1.10,
        swayAmp: 0.040,
        headTilt: 0.080,
        breathSpeed: 2.1,
        specialMorphs: { happy: '笑い', wink: 'ウインク', gentle: '穏やか', confused: '困惑', fluffy: 'にひひ', curious: 'びっくり', thinking: '困惑', surprised: 'びっくり', doubt: '困惑' }
    },
    'ouro_kronii': {
        scale: 0.075,
        cameraDist: 2.95,
        targetYOffset: 0.04,
        hipsY: 1.15,
        armLeft: [0.08, 0.05, -1.26],
        armRight: [0.08, -0.05, 1.26],
        forearmLeft: [0.16, 0.0, 0.10],
        forearmRight: [0.16, 0.0, -0.10],
        swaySpeed: 1.05,
        swayAmp: 0.024,
        headTilt: 0.045,
        breathSpeed: 1.9,
        specialMorphs: { happy: '笑い', proud: '真面目', strict: '怒り', smirk: 'にこり', smug: 'ジト目', curious: 'びっくり', thinking: '真面目', surprised: 'びっくり', doubt: '真面目' }
    },
    'pavolia_reine': {
        scale: 0.084,
        cameraDist: 2.80,
        targetYOffset: 0.03,
        hipsY: 1.06,
        armLeft: [0.10, 0.05, -1.24],
        armRight: [0.10, -0.05, 1.24],
        forearmLeft: [0.18, 0.0, 0.12],
        forearmRight: [0.18, 0.0, -0.12],
        swaySpeed: 1.15,
        swayAmp: 0.030,
        headTilt: 0.060,
        breathSpeed: 2.0,
        specialMorphs: { happy: '笑い', wink: 'ウィンク', elegant: 'キリッ', proud: '真面目', surprise: 'びっくり', curious: 'びっくり', thinking: '真面目', surprised: 'びっくり', doubt: '真面目' }
    },
    'hatsune_miku_v4c': {
        scale: 0.088,
        cameraDist: 2.75,
        targetYOffset: 0.03,
        hipsY: 1.02,
        armLeft: [0.10, 0.04, -1.38],
        armRight: [0.10, -0.04, 1.38],
        forearmLeft: [0.15, 0.00, 0.10],
        forearmRight: [0.15, 0.00, -0.10],
        swaySpeed: 1.35,
        swayAmp: 0.038,
        headTilt: 0.085,
        breathSpeed: 2.4,
        specialMorphs: { happy: '笑い', wink: 'ウィンク', twin: '笑い目', star: '星目', surprise: 'びっくり', curious: 'びっくり', thinking: '困り', surprised: 'びっくり', doubt: '困り' }
    }
};

export class DedicatedPMXController {
    constructor() {
        this.activeProfileKey = 'hoshimachi_suisei';
        this.currentProfile = PMX_MODEL_PROFILES['hoshimachi_suisei'];
        this.mesh = null;
        this.vrm = null;
        this.breathPhase = 0.0;
        this.idleTime = 0.0;
        this.blinkTimer = 3.0;
        this.isBlinking = false;
        this.blinkElapsed = 0.0;
        this.blinkDuration = 0.22;
        this.activeGesture = null;
        this.gestureTime = 0.0;
        this.gestureDuration = 0.0;
        this.gestureTimer = 4.0 + Math.random() * 3.0;
        this.earBones = [];
        this.tailBones = [];
        this.isMusicActive = false;
        this.musicBpm = 120.0;
        this.musicPhase = 0.0;
        this.musicGenre = 'pop';
        this.isWalking = false;
        this.walkSpeed = 1.0;
        this.walkPhase = 0.0;
        this.walkWeight = 0.0;
        this.walkCadence = 5.2;
        this.initialHipsY = null;
    }

    startWalking(speed = 1.0) {
        this.isWalking = true;
        this.walkSpeed = Math.max(0.1, Math.min(2.5, Number(speed) || 1.0));
    }

    stopWalking() {
        this.isWalking = false;
    }

    setWalkSpeed(speed) {
        this.walkSpeed = Math.max(0.1, Math.min(2.5, Number(speed) || 1.0));
    }

    setMusicActive(active, bpm = 120.0) {
        this.isMusicActive = !!active;
        if (bpm) this.musicBpm = Number(bpm) || 120.0;
        if (!this.isMusicActive) {
            this.musicPhase = 0.0;
        }
    }

    setMusicGenre(genre = 'pop', bpm = 120.0) {
        this.musicGenre = (genre || 'pop').toLowerCase();
        if (bpm) this.musicBpm = Number(bpm) || 120.0;
    }

    identifyModelKey(path) {
        const lower = String(path || '').toLowerCase();
        for (const k of Object.keys(PMX_MODEL_PROFILES)) {
            if (lower.includes(k)) return k;
        }
        if (lower.includes('miku') || lower.includes('ミク') || lower.includes('v4c') || lower.includes('野餐')) return 'hatsune_miku_v4c';
        if (lower.includes('suisei') || lower.includes('すいせい') || lower.includes('vanessa')) return 'hoshimachi_suisei';
        if (lower.includes('marine') || lower.includes('マリン')) return 'houshou_marine';
        if (lower.includes('korone') || lower.includes('ころね')) return 'inugami_korone';
        if (lower.includes('okayu') || lower.includes('おかゆ')) return 'nekomata_okayu';
        if (lower.includes('watame') || lower.includes('わため')) return 'tsunomaki_watame';
        if (lower.includes('kronii') || lower.includes('クロニー')) return 'ouro_kronii';
        if (lower.includes('reine')) return 'pavolia_reine';
        return 'hoshimachi_suisei';
    }

    applyModelCalibration(path, mesh, vrm, camera) {
        this.mesh = mesh;
        this.vrm = vrm;
        this.activeProfileKey = this.identifyModelKey(path);
        this.currentProfile = PMX_MODEL_PROFILES[this.activeProfileKey] || PMX_MODEL_PROFILES['hoshimachi_suisei'];
        this.earBones = [];
        this.tailBones = [];
        this.initialHipsY = null;

        if (mesh) {
            mesh.scale.setScalar(this.currentProfile.scale);
            mesh.rotation.y = 0.0;
            this.optimizeMeshMaterials(mesh);
            mesh.traverse((node) => {
                if (node.isBone) {
                    const bn = node.name || '';
                    if (bn.includes('耳') || bn.includes('ear') || bn.includes('Ear')) {
                        this.earBones.push(node);
                    }
                    if (bn.includes('尻尾') || bn.includes('しっぽ') || bn.includes('tail') || bn.includes('Tail')) {
                        this.tailBones.push(node);
                    }
                }
            });
        }

        if (vrm && vrm.humanoid) {
            this.applyRestPose(vrm);
            const hips = vrm.humanoid.getNormalizedBoneNode('hips') || vrm.humanoid.getRawBoneNode('hips');
            if (hips) {
                this.initialHipsY = hips.position.y;
            }
        }

        if (camera && mesh) {
            this.frameCamera(mesh, camera);
        }

        return this.currentProfile;
    }

    applyRestPose(vrm) {
        if (!vrm || !vrm.humanoid) return;
        const p = this.currentProfile;
        const lShoulder = vrm.humanoid.getNormalizedBoneNode('leftShoulder') || vrm.humanoid.getRawBoneNode('leftShoulder');
        const rShoulder = vrm.humanoid.getNormalizedBoneNode('rightShoulder') || vrm.humanoid.getRawBoneNode('rightShoulder');
        const lArm = vrm.humanoid.getNormalizedBoneNode('leftUpperArm') || vrm.humanoid.getRawBoneNode('leftUpperArm');
        const rArm = vrm.humanoid.getNormalizedBoneNode('rightUpperArm') || vrm.humanoid.getRawBoneNode('rightUpperArm');
        const lForearm = vrm.humanoid.getNormalizedBoneNode('leftLowerArm') || vrm.humanoid.getRawBoneNode('leftLowerArm');
        const rForearm = vrm.humanoid.getNormalizedBoneNode('rightLowerArm') || vrm.humanoid.getRawBoneNode('rightLowerArm');
        const lUpperLeg = vrm.humanoid.getNormalizedBoneNode('leftUpperLeg') || vrm.humanoid.getRawBoneNode('leftUpperLeg');
        const rUpperLeg = vrm.humanoid.getNormalizedBoneNode('rightUpperLeg') || vrm.humanoid.getRawBoneNode('rightUpperLeg');
        const lLowerLeg = vrm.humanoid.getNormalizedBoneNode('leftLowerLeg') || vrm.humanoid.getRawBoneNode('leftLowerLeg');
        const rLowerLeg = vrm.humanoid.getNormalizedBoneNode('rightLowerLeg') || vrm.humanoid.getRawBoneNode('rightLowerLeg');

        if (lShoulder) {
            lShoulder.rotation.set(0.02, 0.0, -0.04);
        }
        if (rShoulder) {
            rShoulder.rotation.set(0.02, 0.0, 0.04);
        }
        if (lArm) {
            lArm.rotation.set(p.armLeft[0], p.armLeft[1], p.armLeft[2]);
        }
        if (rArm) {
            rArm.rotation.set(p.armRight[0], p.armRight[1], p.armRight[2]);
        }
        if (lForearm) {
            lForearm.rotation.set(p.forearmLeft[0] || 0.21, p.forearmLeft[1], p.forearmLeft[2]);
        }
        if (rForearm) {
            rForearm.rotation.set(p.forearmRight[0] || 0.21, p.forearmRight[1], p.forearmRight[2]);
        }
        if (lUpperLeg) {
            lUpperLeg.rotation.set(-0.02, 0.0, -0.02);
        }
        if (rUpperLeg) {
            rUpperLeg.rotation.set(-0.02, 0.0, 0.02);
        }
        if (lLowerLeg) {
            lLowerLeg.rotation.set(0.05, 0.0, 0.0);
        }
        if (rLowerLeg) {
            rLowerLeg.rotation.set(0.05, 0.0, 0.0);
        }

        const fingerBones = [
            'leftThumbProximal', 'leftIndexProximal', 'leftMiddleProximal', 'leftRingProximal', 'leftLittleProximal',
            'rightThumbProximal', 'rightIndexProximal', 'rightMiddleProximal', 'rightRingProximal', 'rightLittleProximal'
        ];
        fingerBones.forEach((fname) => {
            const b = vrm.humanoid.getNormalizedBoneNode(fname) || vrm.humanoid.getRawBoneNode(fname);
            if (b) {
                b.rotation.z = fname.includes('left') ? -0.10 : 0.10;
            }
        });
    }

    applyNaturalBindPoseFix(vrm) {
        this.applyRestPose(vrm);
    }

    applyNaturalPostureInitializer(vrm) {
        this.applyRestPose(vrm);
    }

    optimizeMeshMaterials(mesh) {
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
                nName.includes('grid') ||
                nName.includes('ik親') ||
                nName.includes('ｉｋ先') ||
                nName.includes('操作中心') ||
                nName.includes('表示枠')
            ) {
                node.visible = false;
            }

            if (node.isMesh && node.geometry) {
                const geom = node.geometry;
                if (!geom.boundingBox) geom.computeBoundingBox();
                const bb = geom.boundingBox;
                if (bb) {
                    const sz = new THREE.Vector3();
                    bb.getSize(sz);
                    if (sz.length() < 0.18 && bb.max.y <= 0.08) {
                        node.visible = false;
                    }
                }
            }

            if (node.isMesh && node.material) {
                const mats = Array.isArray(node.material) ? node.material : [node.material];
                mats.forEach((mat) => {
                    mat.side = THREE.DoubleSide;
                    if (mat.map) {
                        mat.map.anisotropy = 16;
                        if (mat.map.image) {
                            mat.map.generateMipmaps = true;
                            mat.map.minFilter = THREE.LinearMipmapLinearFilter;
                            mat.map.magFilter = THREE.LinearFilter;
                        }
                    }
                    if (mat.color) {
                        mat.color.setRGB(1.0, 1.0, 1.0);
                    }
                    if (mat.emissive) {
                        mat.emissive.setRGB(0.015, 0.012, 0.010);
                    }
                    mat.roughness = 0.28;
                    mat.metalness = 0.02;
                    mat.alphaTest = 0.05;
                    mat.depthWrite = true;
                    mat.wireframe = false;
                });
            }
        });
    }

    frameCamera(mesh, camera) {
        if (!mesh || !camera) return;
        mesh.updateMatrixWorld(true);
        const box = new THREE.Box3().setFromObject(mesh);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        const p = this.currentProfile || PMX_MODEL_PROFILES['hoshimachi_suisei'];
        const vFovRad = (camera.fov * Math.PI) / 180;
        const hFovRad = 2 * Math.atan(Math.tan(vFovRad / 2) * (camera.aspect || 0.58));
        const distY = (size.y * 1.28) / (2 * Math.tan(vFovRad / 2));
        const distX = (size.x * 1.25) / (2 * Math.tan(hFovRad / 2));
        const dist = Math.max(distY, distX, p.cameraDist || 2.75);
        const targetY = center.y + size.y * (p.targetYOffset !== undefined ? p.targetYOffset : 0.03);
        camera.position.set(0, targetY, dist);
        camera.lookAt(0, targetY, 0);
    }

    setExpression(preset, weight = 1.0) {
        if (!this.vrm || !this.vrm.expressionManager) return;
        const w = THREE.MathUtils.clamp(weight, 0.0, 1.0);
        this.vrm.expressionManager.setValue(preset, w);
        if (this.currentProfile && this.currentProfile.specialMorphs) {
            const sm = this.currentProfile.specialMorphs[preset];
            if (sm) {
                this.vrm.expressionManager.setValue(sm, w);
            }
        }
    }

    normalizeGestureName(name) {
        const lower = String(name || '').toLowerCase();
        if (lower.includes('walk') || lower.includes('camin') || lower.includes('locomot')) return 'walk';
        if (lower.includes('curios') || lower.includes('inclin') || lower.includes('asoma') || lower.includes('lean')) return 'curiosity';
        if (lower.includes('point') || lower.includes('señal') || lower.includes('indica') || lower.includes('palm')) return 'pointing';
        if (lower.includes('pregunta') || lower.includes('quest') || lower.includes('think') || lower.includes('barbilla') || lower.includes('pens')) return 'question';
        if (lower.includes('duda') || lower.includes('doubt') || lower.includes('shrug')) return 'doubt';
        if (lower.includes('shock') || lower.includes('surpris') || lower.includes('asombr') || lower.includes('susto')) return 'shock';
        if (lower.includes('listen') || lower.includes('escuch') || lower.includes('atent')) return 'listen_attentive';
        if (lower.includes('smug') || lower.includes('presum') || lower.includes('tsundere')) return 'smug';
        if (lower.includes('bow') || lower.includes('reverenc')) return 'bow_polite';
        if (lower.includes('wave') || lower.includes('salud') || lower.includes('hola')) return 'wave';
        if (lower.includes('cheer') || lower.includes('fist') || lower.includes('victoria') || lower.includes('jump')) return 'cheer';
        if (lower.includes('nod') || lower.includes('asient')) return 'nod';
        if (lower.includes('tilt')) return 'tilt';
        return 'characteristic';
    }

    triggerGesture(name, duration = 3.0) {
        const lower = String(name || '').toLowerCase();
        if (lower === 'idle' || lower === 'standby' || lower === 'stop') {
            this.stopWalking();
            return;
        }
        const norm = this.normalizeGestureName(name);
        if (norm === 'walk') {
            this.startWalking(1.0);
            return;
        }
        this.activeGesture = norm;
        this.gestureTime = 0.0;
        this.gestureDuration = duration;
        if (norm === 'curiosity') {
            this.setExpression('curious', 0.90);
        } else if (norm === 'pointing') {
            this.setExpression('happy', 0.85);
        } else if (norm === 'question') {
            this.setExpression('thinking', 0.90);
        } else if (norm === 'doubt') {
            this.setExpression('doubt', 0.85);
        } else if (norm === 'shock') {
            this.setExpression('surprised', 1.0);
        } else if (norm === 'listen_attentive') {
            this.setExpression('relaxed', 0.75);
        } else if (norm === 'smug') {
            this.setExpression('smug', 0.95);
        } else if (norm === 'bow_polite') {
            this.setExpression('happy', 0.70);
        } else if (norm === 'wave') {
            this.setExpression('happy', 0.85);
            this.setExpression('wink', 0.50);
        } else if (norm === 'cheer') {
            this.setExpression('happy', 1.0);
        } else if (norm === 'nod') {
            this.setExpression('happy', 0.70);
        }
    }

    updateProceduralDynamics(dt, vrm) {
        if (!vrm || !vrm.humanoid) return;
        const p = this.currentProfile || PMX_MODEL_PROFILES['hoshimachi_suisei'];
        const bSpeed = p.breathSpeed || 2.3;
        const sSpeed = p.swaySpeed || 1.15;
        const sAmp = p.swayAmp || 0.035;
        const hTilt = p.headTilt || 0.07;

        const spine = vrm.humanoid.getNormalizedBoneNode('spine');
        const chest = vrm.humanoid.getNormalizedBoneNode('chest');
        const head = vrm.humanoid.getNormalizedBoneNode('head');
        const neck = vrm.humanoid.getNormalizedBoneNode('neck');
        const hips = vrm.humanoid.getNormalizedBoneNode('hips') || vrm.humanoid.getRawBoneNode('hips');
        const lUpperLeg = vrm.humanoid.getNormalizedBoneNode('leftUpperLeg') || vrm.humanoid.getRawBoneNode('leftUpperLeg');
        const rUpperLeg = vrm.humanoid.getNormalizedBoneNode('rightUpperLeg') || vrm.humanoid.getRawBoneNode('rightUpperLeg');
        const lLowerLeg = vrm.humanoid.getNormalizedBoneNode('leftLowerLeg') || vrm.humanoid.getRawBoneNode('leftLowerLeg');
        const rLowerLeg = vrm.humanoid.getNormalizedBoneNode('rightLowerLeg') || vrm.humanoid.getRawBoneNode('rightLowerLeg');
        const lFoot = vrm.humanoid.getNormalizedBoneNode('leftFoot') || vrm.humanoid.getRawBoneNode('leftFoot');
        const rFoot = vrm.humanoid.getNormalizedBoneNode('rightFoot') || vrm.humanoid.getRawBoneNode('rightFoot');
        const lArm = vrm.humanoid.getNormalizedBoneNode('leftUpperArm') || vrm.humanoid.getRawBoneNode('leftUpperArm');
        const rArm = vrm.humanoid.getNormalizedBoneNode('rightUpperArm') || vrm.humanoid.getRawBoneNode('rightUpperArm');
        const lForearm = vrm.humanoid.getNormalizedBoneNode('leftLowerArm') || vrm.humanoid.getRawBoneNode('leftLowerArm');
        const rForearm = vrm.humanoid.getNormalizedBoneNode('rightLowerArm') || vrm.humanoid.getRawBoneNode('rightLowerArm');

        if (this.isWalking) {
            this.walkWeight = Math.min(1.0, this.walkWeight + dt * 4.0);
        } else {
            this.walkWeight = Math.max(0.0, this.walkWeight - dt * 4.0);
        }

        if (this.walkWeight > 0.001) {
            this.walkPhase += dt * this.walkCadence * this.walkSpeed;
        }

        if (this.isMusicActive) {
            this.musicPhase += dt * (this.musicBpm / 60.0) * Math.PI * 2.0;
            const beat = this.musicPhase;
            const danceSway = Math.sin(beat * 0.5);
            const danceBounce = Math.abs(Math.sin(beat)) * 0.028;
            const dancePitch = Math.cos(beat) * 0.045;

            if (spine) {
                spine.rotation.x = THREE.MathUtils.lerp(spine.rotation.x, dancePitch + 0.04, 0.18);
                spine.rotation.y = THREE.MathUtils.lerp(spine.rotation.y, danceSway * 0.07, 0.18);
                spine.rotation.z = THREE.MathUtils.lerp(spine.rotation.z, -Math.cos(beat * 0.5) * 0.04, 0.18);
            }
            if (chest) {
                chest.rotation.x = THREE.MathUtils.lerp(chest.rotation.x, dancePitch * 0.8, 0.18);
                chest.rotation.y = THREE.MathUtils.lerp(chest.rotation.y, danceSway * 0.05, 0.18);
            }
            if (neck) {
                neck.rotation.x = THREE.MathUtils.lerp(neck.rotation.x, -dancePitch * 0.5, 0.18);
                neck.rotation.y = THREE.MathUtils.lerp(neck.rotation.y, danceSway * 0.08, 0.18);
            }
            if (head) {
                head.rotation.x = THREE.MathUtils.lerp(head.rotation.x, Math.sin(beat) * 0.09, 0.18);
                head.rotation.y = THREE.MathUtils.lerp(head.rotation.y, danceSway * 0.10, 0.18);
                head.rotation.z = THREE.MathUtils.lerp(head.rotation.z, Math.sin(beat * 0.5) * 0.06, 0.18);
            }
            if (lArm && p && p.armLeft) {
                const armBounce = Math.sin(beat) * 0.10;
                lArm.rotation.set(
                    p.armLeft[0] + 0.20 + armBounce,
                    p.armLeft[1] + danceSway * 0.05,
                    p.armLeft[2] + 0.15 + danceSway * 0.08
                );
            }
            if (rArm && p && p.armRight) {
                const armBounce = Math.sin(beat) * 0.10;
                rArm.rotation.set(
                    p.armRight[0] + 0.20 + armBounce,
                    p.armRight[1] - danceSway * 0.05,
                    p.armRight[2] - 0.15 - danceSway * 0.08
                );
            }
            if (lForearm && p && p.forearmLeft) {
                lForearm.rotation.set(
                    p.forearmLeft[0] + 0.45 + Math.sin(beat + 0.5) * 0.15,
                    p.forearmLeft[1],
                    p.forearmLeft[2]
                );
            }
            if (rForearm && p && p.forearmRight) {
                rForearm.rotation.set(
                    p.forearmRight[0] + 0.45 + Math.sin(beat + 0.5) * 0.15,
                    p.forearmRight[1],
                    p.forearmRight[2]
                );
            }
            if (this.earBones.length > 0) {
                const earBounce = Math.sin(beat * 2.0) * 0.12;
                this.earBones.forEach((eb, idx) => {
                    eb.rotation.z = (idx % 2 === 0 ? 1 : -1) * earBounce;
                });
            }
            if (this.tailBones.length > 0) {
                const tailDance = Math.sin(beat) * 0.25;
                this.tailBones.forEach((tb) => {
                    tb.rotation.y = tailDance;
                });
            }
            this.setExpression('happy', 0.85);
            return;
        }

        this.breathPhase += dt * bSpeed;
        this.idleTime += dt;
        const breath = Math.sin(this.breathPhase);
        const sway = Math.sin(this.idleTime * sSpeed);
        const swaySlow = Math.sin(this.idleTime * (sSpeed * 0.55) + 0.4);

        this.gestureTimer -= dt;
        if (this.gestureTimer <= 0.0 && !this.activeGesture && !this.isWalking) {
            const gestures = ['characteristic', 'curiosity', 'nod', 'tilt', 'question', 'happy', 'pointing'];
            const pick = gestures[Math.floor(Math.random() * gestures.length)];
            this.triggerGesture(pick, 2.5 + Math.random() * 2.0);
            this.gestureTimer = 5.0 + Math.random() * 6.0;
        }

        let gestWeight = 0.0;
        if (this.activeGesture) {
            this.gestureTime += dt;
            const progress = this.gestureTime / this.gestureDuration;
            if (progress <= 0.25) {
                gestWeight = progress / 0.25;
            } else if (progress <= 0.75) {
                gestWeight = 1.0;
            } else if (progress <= 1.0) {
                gestWeight = 1.0 - ((progress - 0.75) / 0.25);
            } else {
                this.activeGesture = null;
                gestWeight = 0.0;
            }
        }

        let spineLean = 0.0;
        let chestLean = 0.0;
        let extraHeadZ = 0.0;
        let extraHeadY = 0.0;
        let extraHeadX = 0.0;

        if (this.activeGesture === 'curiosity') {
            spineLean = 0.14 * gestWeight;
            chestLean = 0.09 * gestWeight;
            extraHeadZ = 0.12 * Math.sin(this.gestureTime * 3.0) * gestWeight;
            extraHeadX = 0.08 * gestWeight;
        } else if (this.activeGesture === 'pointing') {
            spineLean = 0.04 * gestWeight;
            extraHeadY = -0.10 * gestWeight;
            extraHeadX = 0.04 * gestWeight;
        } else if (this.activeGesture === 'question') {
            spineLean = 0.03 * gestWeight;
            extraHeadZ = -0.18 * gestWeight;
            extraHeadY = 0.12 * gestWeight;
            extraHeadX = 0.05 * gestWeight;
        } else if (this.activeGesture === 'doubt') {
            spineLean = -0.04 * gestWeight;
            extraHeadZ = 0.20 * Math.sin(this.gestureTime * 2.5) * gestWeight;
            extraHeadY = -0.08 * gestWeight;
        } else if (this.activeGesture === 'shock') {
            spineLean = -0.12 * gestWeight;
            chestLean = -0.06 * gestWeight;
            extraHeadX = -0.10 * gestWeight;
        } else if (this.activeGesture === 'listen_attentive') {
            spineLean = 0.08 * gestWeight;
            chestLean = 0.05 * gestWeight;
            extraHeadZ = 0.10 * gestWeight;
            extraHeadX = 0.04 * gestWeight;
        } else if (this.activeGesture === 'smug') {
            spineLean = -0.06 * gestWeight;
            chestLean = 0.08 * gestWeight;
            extraHeadX = -0.08 * gestWeight;
            extraHeadY = -0.05 * gestWeight;
        } else if (this.activeGesture === 'bow_polite') {
            spineLean = 0.32 * gestWeight;
            chestLean = 0.18 * gestWeight;
            extraHeadX = 0.22 * gestWeight;
        } else if (this.activeGesture === 'wave') {
            extraHeadZ = -0.08 * gestWeight;
            extraHeadY = -0.05 * gestWeight;
        } else if (this.activeGesture === 'cheer') {
            spineLean = -0.05 * gestWeight;
            chestLean = 0.08 * gestWeight;
            extraHeadX = -0.10 * gestWeight;
        } else if (this.activeGesture === 'nod') {
            extraHeadX = Math.sin(this.gestureTime * 6.5) * 0.16 * gestWeight;
        } else if (this.activeGesture === 'tilt') {
            extraHeadZ = 0.18 * Math.sin(this.gestureTime * 3.0) * gestWeight;
        }

        const walkStride = Math.sin(this.walkPhase);
        const walkBounce = Math.abs(Math.sin(this.walkPhase));
        const walkSway = Math.cos(this.walkPhase);
        const wW = this.walkWeight;

        if (hips) {
            if (this.initialHipsY === null) {
                this.initialHipsY = hips.position.y;
            }
            const targetHipsY = this.initialHipsY - (walkBounce * 0.032 * wW);
            hips.position.y = THREE.MathUtils.lerp(hips.position.y, targetHipsY, 0.25);
            const targetHipsZ = walkSway * 0.012 * wW;
            hips.rotation.z = THREE.MathUtils.lerp(hips.rotation.z, targetHipsZ, 0.20);
            hips.rotation.y = THREE.MathUtils.lerp(hips.rotation.y, walkSway * 0.035 * wW, 0.20);
        }

        if (lUpperLeg) {
            const targetPitch = walkStride * 0.42 * wW;
            lUpperLeg.rotation.x = THREE.MathUtils.lerp(lUpperLeg.rotation.x, targetPitch, 0.25);
            lUpperLeg.rotation.z = THREE.MathUtils.lerp(lUpperLeg.rotation.z, -0.02, 0.15);
        }
        if (rUpperLeg) {
            const targetPitch = -walkStride * 0.42 * wW;
            rUpperLeg.rotation.x = THREE.MathUtils.lerp(rUpperLeg.rotation.x, targetPitch, 0.25);
            rUpperLeg.rotation.z = THREE.MathUtils.lerp(rUpperLeg.rotation.z, 0.02, 0.15);
        }
        if (lLowerLeg) {
            const kneeFlex = Math.max(0.0, -walkStride) * 0.58 * wW;
            lLowerLeg.rotation.x = THREE.MathUtils.lerp(lLowerLeg.rotation.x, kneeFlex, 0.25);
        }
        if (rLowerLeg) {
            const kneeFlex = Math.max(0.0, walkStride) * 0.58 * wW;
            rLowerLeg.rotation.x = THREE.MathUtils.lerp(rLowerLeg.rotation.x, kneeFlex, 0.25);
        }
        if (lFoot) {
            const footPitch = walkStride * 0.20 * wW;
            lFoot.rotation.x = THREE.MathUtils.lerp(lFoot.rotation.x, footPitch, 0.25);
        }
        if (rFoot) {
            const footPitch = -walkStride * 0.20 * wW;
            rFoot.rotation.x = THREE.MathUtils.lerp(rFoot.rotation.x, footPitch, 0.25);
        }

        if (spine) {
            const walkSpineTurn = -walkSway * 0.035 * wW;
            spine.rotation.x = THREE.MathUtils.lerp(spine.rotation.x, breath * 0.024 + spineLean, 0.15);
            spine.rotation.y = THREE.MathUtils.lerp(spine.rotation.y, sway * sAmp + walkSpineTurn, 0.10);
            spine.rotation.z = THREE.MathUtils.lerp(spine.rotation.z, -swaySlow * (sAmp * 0.6), 0.10);
        }
        if (chest) {
            chest.rotation.x = THREE.MathUtils.lerp(chest.rotation.x, breath * 0.035 + chestLean, 0.15);
            chest.rotation.y = THREE.MathUtils.lerp(chest.rotation.y, sway * (sAmp * 0.7), 0.10);
        }
        if (neck) {
            neck.rotation.x = THREE.MathUtils.lerp(neck.rotation.x, -breath * 0.016, 0.10);
            neck.rotation.y = THREE.MathUtils.lerp(neck.rotation.y, sway * (sAmp * 1.2), 0.10);
            neck.rotation.z = THREE.MathUtils.lerp(neck.rotation.z, swaySlow * (sAmp * 0.7), 0.10);
        }
        if (head) {
            head.rotation.x = THREE.MathUtils.lerp(head.rotation.x, -breath * 0.022 + extraHeadX, 0.10);
            head.rotation.y = THREE.MathUtils.lerp(head.rotation.y, sway * hTilt + extraHeadY, 0.10);
            head.rotation.z = THREE.MathUtils.lerp(head.rotation.z, swaySlow * (hTilt * 0.6) + extraHeadZ, 0.10);
        }

        if (lArm && p && p.armLeft) {
            let armPoseX = p.armLeft[0];
            let armPoseY = p.armLeft[1];
            let armPoseZ = p.armLeft[2];
            if (this.activeGesture === 'curiosity') {
                armPoseX -= 0.15 * gestWeight;
                armPoseZ -= 0.05 * gestWeight;
            } else if (this.activeGesture === 'pointing') {
                armPoseX += 0.15 * gestWeight;
                armPoseZ += 0.10 * gestWeight;
            } else if (this.activeGesture === 'question') {
                armPoseX += 0.20 * gestWeight;
                armPoseZ += 0.20 * gestWeight;
            } else if (this.activeGesture === 'doubt') {
                armPoseX += 0.30 * gestWeight;
                armPoseZ += 0.35 * gestWeight;
            } else if (this.activeGesture === 'shock') {
                armPoseX -= 0.30 * gestWeight;
                armPoseZ -= 0.25 * gestWeight;
            } else if (this.activeGesture === 'smug') {
                armPoseX += 0.25 * gestWeight;
                armPoseZ += 0.30 * gestWeight;
            } else if (this.activeGesture === 'bow_polite') {
                armPoseX += 0.20 * gestWeight;
                armPoseZ += 0.15 * gestWeight;
            } else if (this.activeGesture === 'cheer') {
                armPoseX -= 0.90 * gestWeight;
                armPoseZ += 0.45 * gestWeight;
            } else if (this.activeGesture === 'characteristic') {
                if (this.activeProfileKey === 'inugami_korone') {
                    armPoseX += 0.35 * gestWeight;
                    armPoseZ += 0.45 * gestWeight;
                } else if (this.activeProfileKey === 'houshou_marine') {
                    armPoseX += 0.20 * gestWeight;
                    armPoseZ -= 0.15 * gestWeight;
                } else if (this.activeProfileKey === 'tsunomaki_watame') {
                    armPoseX += 0.25 * gestWeight;
                    armPoseY += 0.15 * gestWeight;
                }
            }
            const armSway = Math.sin(this.idleTime * (sSpeed * 1.1)) * (sAmp * 1.2);
            const walkArmSwing = -walkStride * 0.35 * wW * (1.0 - gestWeight);
            lArm.rotation.set(armPoseX + armSway + walkArmSwing, armPoseY + sway * 0.015, armPoseZ + armSway * 0.6);
        }

        if (rArm && p && p.armRight) {
            let armPoseX = p.armRight[0];
            let armPoseY = p.armRight[1];
            let armPoseZ = p.armRight[2];
            if (this.activeGesture === 'curiosity') {
                armPoseX -= 0.15 * gestWeight;
                armPoseZ += 0.05 * gestWeight;
            } else if (this.activeGesture === 'pointing') {
                armPoseX -= 0.90 * gestWeight;
                armPoseY -= 0.15 * gestWeight;
                armPoseZ -= 0.45 * gestWeight;
            } else if (this.activeGesture === 'question') {
                armPoseX -= 0.55 * gestWeight;
                armPoseY -= 0.20 * gestWeight;
                armPoseZ -= 0.55 * gestWeight;
            } else if (this.activeGesture === 'doubt') {
                armPoseX += 0.30 * gestWeight;
                armPoseZ -= 0.35 * gestWeight;
            } else if (this.activeGesture === 'shock') {
                armPoseX -= 0.30 * gestWeight;
                armPoseZ += 0.25 * gestWeight;
            } else if (this.activeGesture === 'smug') {
                armPoseX += 0.25 * gestWeight;
                armPoseZ -= 0.30 * gestWeight;
            } else if (this.activeGesture === 'bow_polite') {
                armPoseX += 0.20 * gestWeight;
                armPoseZ -= 0.15 * gestWeight;
            } else if (this.activeGesture === 'wave') {
                armPoseX -= 0.85 * gestWeight;
                armPoseZ -= 0.60 * gestWeight;
            } else if (this.activeGesture === 'cheer') {
                armPoseX -= 0.90 * gestWeight;
                armPoseZ -= 0.45 * gestWeight;
            } else if (this.activeGesture === 'characteristic') {
                if (this.activeProfileKey === 'inugami_korone') {
                    armPoseX += 0.35 * gestWeight;
                    armPoseZ -= 0.45 * gestWeight;
                } else if (this.activeProfileKey === 'houshou_marine') {
                    armPoseX += 0.20 * gestWeight;
                    armPoseZ += 0.15 * gestWeight;
                } else if (this.activeProfileKey === 'hoshimachi_suisei') {
                    armPoseX += 0.30 * gestWeight;
                    armPoseY -= 0.20 * gestWeight;
                }
            }
            const armSway = Math.sin(this.idleTime * (sSpeed * 1.1)) * (sAmp * 1.2);
            const walkArmSwing = walkStride * 0.35 * wW * (1.0 - gestWeight);
            rArm.rotation.set(armPoseX + armSway + walkArmSwing, armPoseY - sway * 0.015, armPoseZ - armSway * 0.6);
        }

        if (lForearm && p && p.forearmLeft) {
            let forePoseX = p.forearmLeft[0];
            let forePoseY = p.forearmLeft[1];
            let forePoseZ = p.forearmLeft[2];
            if (this.activeGesture === 'curiosity') {
                forePoseX += 0.15 * gestWeight;
            } else if (this.activeGesture === 'smug') {
                forePoseX += 0.55 * gestWeight;
            } else if (this.activeGesture === 'doubt') {
                forePoseX += 0.65 * gestWeight;
            } else if (this.activeGesture === 'bow_polite') {
                forePoseX += 0.45 * gestWeight;
            } else if (this.activeGesture === 'cheer') {
                forePoseX += 0.50 * gestWeight;
            } else if (this.activeGesture === 'characteristic' && (this.activeProfileKey === 'inugami_korone' || this.activeProfileKey === 'nekomata_okayu')) {
                forePoseX += 0.40 * gestWeight;
            }
            const foreSway = Math.sin(this.idleTime * (sSpeed * 1.1) + 0.4) * 0.030;
            const walkForeFlex = Math.max(0.0, -walkStride) * 0.22 * wW * (1.0 - gestWeight);
            lForearm.rotation.set(forePoseX + foreSway + walkForeFlex, forePoseY, forePoseZ);
        }

        if (rForearm && p && p.forearmRight) {
            let forePoseX = p.forearmRight[0];
            let forePoseY = p.forearmRight[1];
            let forePoseZ = p.forearmRight[2];
            if (this.activeGesture === 'curiosity') {
                forePoseX += 0.15 * gestWeight;
            } else if (this.activeGesture === 'pointing') {
                forePoseX -= 0.10 * gestWeight;
            } else if (this.activeGesture === 'question') {
                forePoseX += 1.05 * gestWeight;
                forePoseY += 0.35 * gestWeight;
            } else if (this.activeGesture === 'smug') {
                forePoseX += 0.55 * gestWeight;
            } else if (this.activeGesture === 'doubt') {
                forePoseX += 0.65 * gestWeight;
            } else if (this.activeGesture === 'bow_polite') {
                forePoseX += 0.45 * gestWeight;
            } else if (this.activeGesture === 'wave') {
                forePoseX += 0.85 * gestWeight;
                forePoseZ += Math.sin(this.gestureTime * 8.0) * 0.25 * gestWeight;
            } else if (this.activeGesture === 'cheer') {
                forePoseX += 0.50 * gestWeight;
            } else if (this.activeGesture === 'characteristic' && (this.activeProfileKey === 'inugami_korone' || this.activeProfileKey === 'nekomata_okayu')) {
                forePoseX += 0.40 * gestWeight;
            }
            const foreSway = Math.sin(this.idleTime * (sSpeed * 1.1) + 0.4) * 0.030;
            const walkForeFlex = Math.max(0.0, walkStride) * 0.22 * wW * (1.0 - gestWeight);
            rForearm.rotation.set(forePoseX + foreSway + walkForeFlex, forePoseY, forePoseZ);
        }

        if (vrm.humanoid) {
            const curlTargets = ['rightThumbProximal', 'rightMiddleProximal', 'rightRingProximal', 'rightLittleProximal'];
            curlTargets.forEach(fn => {
                const b = vrm.humanoid.getNormalizedBoneNode(fn) || vrm.humanoid.getRawBoneNode(fn);
                if (b) {
                    if (this.activeGesture === 'pointing') {
                        b.rotation.z = THREE.MathUtils.lerp(b.rotation.z, 0.70 * gestWeight, 0.20);
                    } else {
                        b.rotation.z = THREE.MathUtils.lerp(b.rotation.z, 0.08, 0.15);
                    }
                }
            });
            const indexBone = vrm.humanoid.getNormalizedBoneNode('rightIndexProximal') || vrm.humanoid.getRawBoneNode('rightIndexProximal');
            if (indexBone) {
                indexBone.rotation.z = THREE.MathUtils.lerp(indexBone.rotation.z, 0.0, 0.20);
            }
        }

        if (this.earBones.length > 0) {
            const earTwitch = Math.sin(this.idleTime * 4.5) * 0.06;
            this.earBones.forEach((eb, idx) => {
                eb.rotation.z = (idx % 2 === 0 ? 1 : -1) * earTwitch;
            });
        }
        if (this.tailBones.length > 0) {
            const tailWag = Math.sin(this.idleTime * 3.2) * 0.16 + (walkSway * 0.12 * wW);
            this.tailBones.forEach((tb) => {
                tb.rotation.y = tailWag;
                tb.rotation.z = Math.cos(this.idleTime * 1.6) * 0.05;
            });
        }

        this.blinkTimer -= dt;
        if (this.blinkTimer <= 0.0 && !this.isBlinking) {
            this.isBlinking = true;
            this.blinkElapsed = 0.0;
        }
        if (this.isBlinking) {
            this.blinkElapsed += dt;
            const progress = this.blinkElapsed / this.blinkDuration;
            let blinkVal = 0.0;
            if (progress <= 0.5) {
                blinkVal = progress / 0.5;
            } else if (progress <= 1.0) {
                blinkVal = 1.0 - ((progress - 0.5) / 0.5);
            } else {
                this.isBlinking = false;
                this.blinkTimer = 2.0 + Math.random() * 3.5;
                blinkVal = 0.0;
            }
            if (vrm.expressionManager) {
                vrm.expressionManager.setValue('blink', blinkVal);
            }
        }
    }
}
