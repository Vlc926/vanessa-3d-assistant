import * as THREE from 'three';

export class AnimeFXRenderer {
    constructor(scene) {
        this.scene = scene;
        this.fxGroup = new THREE.Group();
        if (this.scene) this.scene.add(this.fxGroup);

        this.sweatSprite = null;
        this.angerSprite = null;
        this.poofParticles = [];

        this.eyeMode = 'normal';
        this.vrm = null;

        this._initTextures();
    }

    setVrm(vrm) {
        this.vrm = vrm;
    }

    _createCanvasTexture(drawer) {
        const canvas = document.createElement('canvas');
        canvas.width = 128;
        canvas.height = 128;
        const ctx = canvas.getContext('2d');
        drawer(ctx, 128, 128);
        const tex = new THREE.CanvasTexture(canvas);
        tex.needsUpdate = true;
        return tex;
    }

    _initTextures() {
        this.sweatTex = this._createCanvasTexture((ctx, w, h) => {
            ctx.clearRect(0, 0, w, h);
            ctx.fillStyle = '#60a5fa';
            ctx.beginPath();
            ctx.moveTo(w * 0.5, h * 0.1);
            ctx.bezierCurveTo(w * 0.85, h * 0.55, w * 0.85, h * 0.85, w * 0.5, h * 0.95);
            ctx.bezierCurveTo(w * 0.15, h * 0.85, w * 0.15, h * 0.55, w * 0.5, h * 0.1);
            ctx.fill();
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(w * 0.42, h * 0.65, w * 0.12, 0, Math.PI * 2);
            ctx.fill();
        });

        this.angerTex = this._createCanvasTexture((ctx, w, h) => {
            ctx.clearRect(0, 0, w, h);
            ctx.strokeStyle = '#ef4444';
            ctx.lineWidth = 14;
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.arc(w * 0.5 - 20, h * 0.5 - 20, 24, 0, Math.PI * 0.5);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(w * 0.5 + 20, h * 0.5 - 20, 24, Math.PI * 0.5, Math.PI);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(w * 0.5 + 20, h * 0.5 + 20, 24, Math.PI, Math.PI * 1.5);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(w * 0.5 - 20, h * 0.5 + 20, 24, Math.PI * 1.5, Math.PI * 2);
            ctx.stroke();
        });
    }

    trigger(type) {
        if (type === 'sweat') this.triggerSweatDrop();
        else if (type === 'anger') this.triggerAngerVein();
    }

    triggerSweatDrop() {
        if (!this.sweatSprite) {
            const mat = new THREE.SpriteMaterial({ map: this.sweatTex, transparent: true, opacity: 0.95 });
            this.sweatSprite = new THREE.Sprite(mat);
            this.sweatSprite.scale.set(0.18, 0.24, 1.0);
            this.fxGroup.add(this.sweatSprite);
        }
        this.sweatTimer = 3.5;
    }

    triggerAngerVein() {
        if (!this.angerSprite) {
            const mat = new THREE.SpriteMaterial({ map: this.angerTex, transparent: true, opacity: 0.95 });
            this.angerSprite = new THREE.Sprite(mat);
            this.angerSprite.scale.set(0.22, 0.22, 1.0);
            this.fxGroup.add(this.angerSprite);
        }
        this.angerTimer = 3.0;
    }

    triggerShockBurst() {
    }

    setEyeMode(mode) {
        this.eyeMode = mode;
        if (!this.vrm) return;
        if (mode === 'spiral' || mode === 'star') {
            if (this.vrm.expressionManager) {
                try {
                    this.vrm.expressionManager.setValue('surprised', 0.95);
                } catch (e) {}
            }
        }
    }

    resetAll() {
        if (this.sweatSprite) {
            this.fxGroup.remove(this.sweatSprite);
            this.sweatSprite = null;
        }
        if (this.angerSprite) {
            this.fxGroup.remove(this.angerSprite);
            this.angerSprite = null;
        }
        this.eyeMode = 'normal';
    }

    update(dt) {
        let headPos = new THREE.Vector3(0, 1.4, 0);
        if (this.vrm && this.vrm.humanoid) {
            const head = this.vrm.humanoid.getNormalizedBoneNode('head') || this.vrm.humanoid.getRawBoneNode('head');
            if (head) head.getWorldPosition(headPos);
        }

        if (this.sweatSprite) {
            this.sweatTimer -= dt;
            this.sweatSprite.position.set(headPos.x + 0.18, headPos.y + 0.12, headPos.z + 0.15);
            if (this.sweatTimer <= 0) {
                this.fxGroup.remove(this.sweatSprite);
                this.sweatSprite = null;
            }
        }

        if (this.angerSprite) {
            this.angerTimer -= dt;
            const pulse = 1.0 + Math.sin(performance.now() * 0.015) * 0.18;
            this.angerSprite.scale.set(0.22 * pulse, 0.22 * pulse, 1.0);
            this.angerSprite.position.set(headPos.x - 0.18, headPos.y + 0.16, headPos.z + 0.15);
            if (this.angerTimer <= 0) {
                this.fxGroup.remove(this.angerSprite);
                this.angerSprite = null;
            }
        }

        for (let i = this.poofParticles.length - 1; i >= 0; i--) {
            const p = this.poofParticles[i];
            p.userData.age += dt;
            const progress = p.userData.age / p.userData.life;
            p.position.addScaledVector(p.userData.vel, dt);
            p.material.opacity = Math.max(0.0, 0.85 * (1.0 - progress));
            const curScale = p.scale.x * (1.0 + dt * 2.0);
            p.scale.set(curScale, curScale, 1.0);

            if (p.userData.age >= p.userData.life) {
                this.fxGroup.remove(p);
                this.poofParticles.splice(i, 1);
            }
        }
    }
}
