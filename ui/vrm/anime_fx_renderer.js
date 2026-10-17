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

        this.sparkleTex = this._createCanvasTexture((ctx, w, h) => {
            ctx.clearRect(0, 0, w, h);
            const cx = w * 0.5;
            const cy = h * 0.5;
            const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, w * 0.45);
            grad.addColorStop(0.0, 'rgba(255, 255, 255, 1.0)');
            grad.addColorStop(0.35, 'rgba(254, 240, 138, 0.95)');
            grad.addColorStop(0.75, 'rgba(250, 204, 21, 0.6)');
            grad.addColorStop(1.0, 'rgba(234, 179, 8, 0.0)');
            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.moveTo(cx, cy - h * 0.45);
            ctx.quadraticCurveTo(cx, cy, cx + w * 0.45, cy);
            ctx.quadraticCurveTo(cx, cy, cx, cy + h * 0.45);
            ctx.quadraticCurveTo(cx, cy, cx - w * 0.45, cy);
            ctx.quadraticCurveTo(cx, cy, cx, cy - h * 0.45);
            ctx.fill();
        });
    }

    trigger(type, options = {}) {
        if (type === 'sweat') this.triggerSweatDrop();
        else if (type === 'anger') this.triggerAngerVein();
        else if (type === 'sparkle' || type === 'sparkles') this.triggerSparkles(options.count || 7);
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

    triggerSparkles(count = 7) {
        let headPos = new THREE.Vector3(0, 1.4, 0);
        if (this.vrm && this.vrm.humanoid) {
            const head = this.vrm.humanoid.getNormalizedBoneNode('head') || this.vrm.humanoid.getRawBoneNode('head');
            if (head) head.getWorldPosition(headPos);
        }
        for (let i = 0; i < count; i++) {
            const mat = new THREE.SpriteMaterial({ map: this.sparkleTex, transparent: true, opacity: 0.95, blending: THREE.AdditiveBlending });
            const sprite = new THREE.Sprite(mat);
            const offsetX = (Math.random() - 0.5) * 0.38;
            const offsetY = Math.random() * 0.25 + 0.05;
            const offsetZ = (Math.random() - 0.5) * 0.25 + 0.10;
            sprite.position.set(headPos.x + offsetX, headPos.y + offsetY, headPos.z + offsetZ);
            const initScale = 0.10 + Math.random() * 0.08;
            sprite.scale.set(initScale, initScale, 1.0);
            sprite.userData = {
                isSparkle: true,
                age: 0.0,
                life: 1.1 + Math.random() * 0.7,
                baseScale: initScale,
                velY: 0.12 + Math.random() * 0.14,
                velX: (Math.random() - 0.5) * 0.08,
                rotSpeed: (Math.random() - 0.5) * 4.0
            };
            this.fxGroup.add(sprite);
            this.poofParticles.push(sprite);
        }
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
            if (p.userData.isSparkle) {
                p.position.y += p.userData.velY * dt;
                p.position.x += p.userData.velX * dt;
                p.material.rotation += p.userData.rotSpeed * dt;
                const pulse = 1.0 + Math.sin(p.userData.age * 9.0) * 0.25;
                const sc = p.userData.baseScale * pulse * Math.sin(progress * Math.PI);
                p.scale.set(sc, sc, 1.0);
                p.material.opacity = Math.max(0.0, Math.sin(progress * Math.PI));
            } else {
                p.position.addScaledVector(p.userData.vel, dt);
                p.material.opacity = Math.max(0.0, 0.85 * (1.0 - progress));
                const curScale = p.scale.x * (1.0 + dt * 2.0);
                p.scale.set(curScale, curScale, 1.0);
            }

            if (p.userData.age >= p.userData.life) {
                this.fxGroup.remove(p);
                this.poofParticles.splice(i, 1);
            }
        }
    }
}
