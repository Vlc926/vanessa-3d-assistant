import * as THREE from 'three';
import { createVRMAnimationClip } from '@pixiv/three-vrm-animation';
import { getMotionConfig } from './personality_kinematics.js';
import { NaturalBindPoseFix, VRMARetargeter } from './AvatarAdapter.js';

export class AnimationController {
    constructor(loader) {
        this.loader = loader;
        this.mixer = null;
        this.vrm = null;
        this.avatarAdapter = null;
        this.bridge = null;
        this.rawVrmaCache = new Map();
        this.retargetedCache = new Map();
        this.currentAction = null;
        this.currentMotionName = 'idle';
        this.standbyName = 'idle_loop';
        this.activeFinishedListener = null;
        this.pendingReturnTimer = null;
        this.walkSpeed = 1.0;
        this.onExpressionRequested = null;
    }

    setVrm(vrm, avatarAdapter = null) {
        this.vrm = vrm;
        this.avatarAdapter = avatarAdapter;
        this.retargetedCache.clear();
        this.currentAction = null;
        this.currentMotionName = 'idle';
        if (this.pendingReturnTimer) {
            clearTimeout(this.pendingReturnTimer);
            this.pendingReturnTimer = null;
        }
        if (vrm && vrm.scene) {
            this.mixer = new THREE.AnimationMixer(vrm.scene);
            const hipsNode = vrm.humanoid ? (vrm.humanoid.getNormalizedBoneNode('hips') || vrm.humanoid.getRawBoneNode('hips')) : null;
            this.bindHipsY = hipsNode ? hipsNode.position.y : undefined;
            if (vrm.humanoid) {
                this.applyNaturalRestPose(vrm);
            }
            const procedural = this.createProceduralIdleClip();
            if (procedural) {
                const action = this.mixer.clipAction(procedural);
                action.setLoop(THREE.LoopRepeat, Infinity);
                action.play();
                this.currentAction = action;
            }
        } else {
            this.mixer = null;
            this.bindHipsY = undefined;
        }
    }

    applyNaturalRestPose(vrm) {
        if (!vrm || !vrm.humanoid) return;
        NaturalBindPoseFix(vrm);
    }

    createProceduralIdleClip() {
        if (!this.vrm || !this.vrm.humanoid) return null;
        const tracks = [];
        const times = [0, 1.5, 3.0];
        const lArm = this.vrm.humanoid.getNormalizedBoneNode('leftUpperArm') || this.vrm.humanoid.getRawBoneNode('leftUpperArm');
        const rArm = this.vrm.humanoid.getNormalizedBoneNode('rightUpperArm') || this.vrm.humanoid.getRawBoneNode('rightUpperArm');
        const lForearm = this.vrm.humanoid.getNormalizedBoneNode('leftLowerArm') || this.vrm.humanoid.getRawBoneNode('leftLowerArm');
        const rForearm = this.vrm.humanoid.getNormalizedBoneNode('rightLowerArm') || this.vrm.humanoid.getRawBoneNode('rightLowerArm');
        const spine = this.vrm.humanoid.getNormalizedBoneNode('spine') || this.vrm.humanoid.getRawBoneNode('spine');
        const head = this.vrm.humanoid.getNormalizedBoneNode('head') || this.vrm.humanoid.getRawBoneNode('head');
        if (lArm) {
            const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.1, 0.05, -1.25));
            const vals = [q.x, q.y, q.z, q.w, q.x, q.y, q.z, q.w, q.x, q.y, q.z, q.w];
            tracks.push(new THREE.QuaternionKeyframeTrack(`${lArm.name}.quaternion`, times, vals));
        }
        if (rArm) {
            const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.1, -0.05, 1.25));
            const vals = [q.x, q.y, q.z, q.w, q.x, q.y, q.z, q.w, q.x, q.y, q.z, q.w];
            tracks.push(new THREE.QuaternionKeyframeTrack(`${rArm.name}.quaternion`, times, vals));
        }
        if (lForearm) {
            const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.2, 0.0, 0.15));
            const vals = [q.x, q.y, q.z, q.w, q.x, q.y, q.z, q.w, q.x, q.y, q.z, q.w];
            tracks.push(new THREE.QuaternionKeyframeTrack(`${lForearm.name}.quaternion`, times, vals));
        }
        if (rForearm) {
            const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.2, 0.0, -0.15));
            const vals = [q.x, q.y, q.z, q.w, q.x, q.y, q.z, q.w, q.x, q.y, q.z, q.w];
            tracks.push(new THREE.QuaternionKeyframeTrack(`${rForearm.name}.quaternion`, times, vals));
        }
        if (spine) {
            const q1 = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.015, 0, 0));
            const q2 = new THREE.Quaternion().setFromEuler(new THREE.Euler(-0.01, 0, 0));
            const vals = [q1.x, q1.y, q1.z, q1.w, q2.x, q2.y, q2.z, q2.w, q1.x, q1.y, q1.z, q1.w];
            tracks.push(new THREE.QuaternionKeyframeTrack(`${spine.name}.quaternion`, times, vals));
        }
        if (head) {
            const q1 = new THREE.Quaternion().setFromEuler(new THREE.Euler(-0.01, 0, 0.02));
            const q2 = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.01, 0, -0.01));
            const vals = [q1.x, q1.y, q1.z, q1.w, q2.x, q2.y, q2.z, q2.w, q1.x, q1.y, q1.z, q1.w];
            tracks.push(new THREE.QuaternionKeyframeTrack(`${head.name}.quaternion`, times, vals));
        }
        if (tracks.length === 0) return null;
        return new THREE.AnimationClip('procedural_idle', 3.0, tracks);
    }

    setBridge(bridge) {
        this.bridge = bridge;
    }

    setStandby(name) {
        if (name) this.standbyName = name;
    }

    setWalkSpeed(speed) {
        this.walkSpeed = Math.max(0.5, Math.min(2.5, Number(speed) || 1.0));
        if (this.currentAction && this.currentMotionName.includes('walk')) {
            this.currentAction.setEffectiveTimeScale(this.walkSpeed);
        }
    }

    async loadClip(url) {
        if (!this.vrm || !url) return null;
        if (this.retargetedCache.has(url)) {
            return this.retargetedCache.get(url);
        }
        const promise = (async () => {
            try {
                let vrmAnimation = this.rawVrmaCache.get(url);
                if (!vrmAnimation) {
                    const gltf = await this.loader.loadAsync(url);
                    vrmAnimation = gltf.userData.vrmAnimations?.[0];
                    if (!vrmAnimation) return null;
                    this.rawVrmaCache.set(url, vrmAnimation);
                }
                if (!this.vrm.meta) {
                    this.vrm.meta = { metaVersion: '0' };
                }
                let clip = createVRMAnimationClip(vrmAnimation, this.vrm);
                if (this.avatarAdapter) {
                    clip = VRMARetargeter.retargetClipToAvatar(clip, this.avatarAdapter);
                }
                if (clip && clip.tracks) {
                    clip.tracks = clip.tracks.filter(track => {
                        const lower = track.name.toLowerCase();
                        if (track.name.endsWith('.position')) {
                            if (lower.includes('hips') || lower.includes('root')) {
                                if (track.values && track.values.length >= 3) {
                                    const baseFirstY = track.values[1];
                                    const targetY = (this.bindHipsY !== undefined) ? this.bindHipsY : baseFirstY;
                                    for (let vi = 0; vi < track.values.length; vi += 3) {
                                        track.values[vi] = 0;
                                        const dy = track.values[vi + 1] - baseFirstY;
                                        track.values[vi + 1] = targetY + dy;
                                        track.values[vi + 2] = 0;
                                    }
                                }
                                return true;
                            }
                            return false;
                        }
                        return true;
                    });
                }
                return clip;
            } catch (err) {
                console.error('[AnimationController] Error loading clip:', url, err);
                return this.createProceduralIdleClip();
            }
        })();
        this.retargetedCache.set(url, promise);
        return promise;
    }

    async playMotion(name, customTransition = null) {
        if (!this.vrm || !this.mixer) return false;
        const normName = (name || 'idle').toLowerCase();
        const config = getMotionConfig(normName) || getMotionConfig('idle');
        if (!config) return false;
        const isLoop = config.loop;
        if (this.currentAction && this.currentMotionName === normName && isLoop && this.currentAction.isRunning()) {
            return true;
        }
        if (this.pendingReturnTimer) {
            clearTimeout(this.pendingReturnTimer);
            this.pendingReturnTimer = null;
        }
        if (this.activeFinishedListener && this.mixer) {
            this.mixer.removeEventListener('finished', this.activeFinishedListener);
            this.activeFinishedListener = null;
        }
        const clip = await this.loadClip(config.file);
        if (!clip || !this.mixer) return false;
        const nextAction = this.mixer.clipAction(clip);
        nextAction.setLoop(isLoop ? THREE.LoopRepeat : THREE.LoopOnce, isLoop ? Infinity : 1);
        nextAction.clampWhenFinished = !isLoop;
        const speed = normName.includes('walk') ? this.walkSpeed : 1.0;
        nextAction.setEffectiveTimeScale(speed);
        nextAction.setEffectiveWeight(1.0);
        nextAction.enabled = true;
        const trans = customTransition !== null ? customTransition : (isLoop ? 0.30 : 0.28);
        const prevAction = this.currentAction;
        nextAction.reset();
        if (prevAction && prevAction !== nextAction) {
            prevAction.crossFadeTo(nextAction, trans, true);
        } else {
            nextAction.fadeIn(trans);
        }
        nextAction.play();
        this.currentAction = nextAction;
        this.currentMotionName = normName;
        if (config.expr && this.onExpressionRequested) {
            this.onExpressionRequested(config.expr, config.weight || 0.85);
        }
        const clipDur = clip.duration || 3.0;
        if (this.bridge && this.bridge.on_animation_started) {
            this.bridge.on_animation_started(normName, clipDur);
        }
        if (!isLoop) {
            const returnCrossfade = Math.min(0.32, clipDur * 0.25);
            const delayMs = Math.max(300, (clipDur - returnCrossfade) * 1000);
            this.pendingReturnTimer = setTimeout(() => {
                this.pendingReturnTimer = null;
                if (this.currentMotionName === normName) {
                    this.playMotion(this.standbyName, 0.30);
                }
            }, delayMs);
            this.activeFinishedListener = (e) => {
                if (e.action === nextAction) {
                    if (this.activeFinishedListener && this.mixer) {
                        this.mixer.removeEventListener('finished', this.activeFinishedListener);
                        this.activeFinishedListener = null;
                    }
                    if (this.bridge && this.bridge.on_animation_finished) {
                        this.bridge.on_animation_finished(normName);
                    }
                    if (this.currentMotionName === normName) {
                        this.playMotion(this.standbyName, 0.30);
                    }
                }
            };
            this.mixer.addEventListener('finished', this.activeFinishedListener);
        }
        return true;
    }

    async preloadClips(fileList) {
        const unique = [...new Set(fileList)];
        for (let i = 0; i < unique.length; i += 4) {
            const batch = unique.slice(i, i + 4);
            await Promise.all(batch.map(url => this.loadClip(url).catch(() => null)));
            await new Promise(r => setTimeout(r, 16));
        }
    }

    update(dt) {
        if (this.mixer) {
            this.mixer.update(dt);
        }
    }
}
