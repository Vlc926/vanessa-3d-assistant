import * as THREE from 'three';

export class SensoryPerceptionBroker {
    constructor(gazeController, emotionEngine, animeFxRenderer, chibiModifier) {
        this.gazeController = gazeController;
        this.emotionEngine = emotionEngine;
        this.animeFx = animeFxRenderer;
        this.chibiMod = chibiModifier;

        this.currentSalience = 0.0;
        this.targetSalience = 0.0;
        this.currentTier = 1;
        this.decayRate = 0.25;

        this.screenFocusWindow = null;
        this.activeMedia = null;
        this.lastEventTime = performance.now();
    }

    calculateSalience(valence, arousal, intensity) {
        const v = Math.max(0.0, Math.min(1.0, Math.abs(Number(valence) || 0.0)));
        const a = Math.max(0.0, Math.min(1.0, Number(arousal) || 0.0));
        const i = Math.max(0.0, Math.min(1.0, Number(intensity) || 0.0));
        return Math.max(0.0, Math.min(1.0, (0.35 * v) + (0.40 * a) + (0.25 * i)));
    }

    processEvent(packet) {
        if (!packet || typeof packet !== 'object') return;
        this.lastEventTime = performance.now();

        const type = packet.type;
        const data = packet.data || {};
        let salience = Number(packet.salience) || 0.0;

        if (type === 'text_stimulus') {
            const val = Number(data.emotional_valence) || 0.0;
            const aro = Number(data.arousal) || 0.0;
            const intn = Number(data.intensity) || 0.0;
            salience = Math.max(salience, this.calculateSalience(val, aro, intn));
            this.targetSalience = Math.max(this.targetSalience, salience);

            if (this.emotionEngine) {
                this.emotionEngine.evaluateStimulus(val, aro, intn, salience, data.content_category);
            }
        } else if (type === 'screen_context') {
            this.screenFocusWindow = data;
            const bbox = data.bounding_box || [0, 0, 1920, 1080];
            const sw = window.innerWidth || 1920;
            const sh = window.innerHeight || 1080;
            const cx = (bbox[0] + (bbox[2] / 2)) / sw;
            const cy = (bbox[1] + (bbox[3] / 2)) / sh;
            const normX = (cx - 0.5) * 2.0;
            const normY = -(cy - 0.5) * 2.0;

            if (this.gazeController && data.focus_state) {
                this.gazeController.lookAt(normX, normY, salience);
            }
            this.targetSalience = Math.max(this.targetSalience, salience);
        } else if (type === 'media_stream') {
            this.activeMedia = data;
            const loudness = Number(data.perceived_loudness) || 0.0;
            const bpm = Number(data.tempo_bpm) || 120.0;
            this.targetSalience = Math.max(this.targetSalience, salience);

            if (this.emotionEngine) {
                this.emotionEngine.evaluateMedia(data.media_type, loudness, bpm);
            }
        } else if (type === 'cursor_proximity') {
            const dist = Number(data.distance_to_avatar) || 500.0;
            const normDist = Math.max(0.0, Math.min(1.0, 1.0 - (dist / 800.0)));
            const cx = Number(data.cursor_x) || 0.0;
            const cy = Number(data.cursor_y) || 0.0;
            const sw = window.innerWidth || 1920;
            const sh = window.innerHeight || 1080;
            const gazeX = ((cx / sw) - 0.5) * 2.0;
            const gazeY = -((cy / sh) - 0.5) * 2.0;

            if (this.gazeController) {
                this.gazeController.lookAt(gazeX, gazeY, normDist);
            }
            if (normDist > 0.85 && this.emotionEngine) {
                this.emotionEngine.triggerCursorStartle();
            }
        }
    }

    update(dt) {
        if (this.currentSalience < this.targetSalience) {
            this.currentSalience = Math.min(this.targetSalience, this.currentSalience + dt * 3.5);
        } else if (this.currentSalience > 0.0) {
            this.currentSalience = Math.max(0.0, this.currentSalience - dt * this.decayRate);
            this.targetSalience = Math.max(0.0, this.targetSalience - dt * (this.decayRate * 1.5));
        }

        if (this.emotionEngine) {
            this.emotionEngine.update(dt, this.currentSalience);
        }
    }
}
