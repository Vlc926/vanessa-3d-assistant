export class HierarchicalEmotionEngine {
    constructor(animController, animeFxRenderer, chibiModifier) {
        this.animController = animController;
        this.animeFx = animeFxRenderer;
        this.chibiMod = chibiModifier;

        this.currentTier = 1;
        this.tierHoldTimer = 0.0;
        this.minHoldTime = 3.5;
        this.hysteresisExitThreshold = 0.55;

        this.activeValence = 0.0;
        this.activeArousal = 0.0;
        this.activeIntensity = 0.0;
        this.activeSalience = 0.0;

        this.breathingPhase = 0.0;
        this.breathingRate = 2.4;

        this.onTierChange = null;
    }

    evaluateStimulus(valence, arousal, intensity, salience, category) {
        this.activeValence = Number(valence) || 0.0;
        this.activeArousal = Number(arousal) || 0.0;
        this.activeIntensity = Number(intensity) || 0.0;
        this.activeSalience = Number(salience) || 0.0;

        if (this.activeSalience >= 0.78) {
            this.transitionToTier(3);
            if (this.activeValence < -0.2) {
                if (this.animeFx) this.animeFx.triggerSweatDrop();
                if (this.animeFx) this.animeFx.setEyeMode('spiral');
            } else {
                if (this.animeFx) this.animeFx.setEyeMode('star');
            }
        } else if (this.activeSalience >= 0.40) {
            this.transitionToTier(2);
            if (this.activeValence < -0.3) {
                if (this.animeFx) this.animeFx.triggerAngerVein();
            } else if (this.activeValence > 0.4) {
                if (this.animeFx) this.animeFx.setEyeMode('sparkle');
            }
        } else {
            if (this.currentTier === 1) {
                this.transitionToTier(1);
            }
        }
    }

    evaluateMedia(mediaType, loudness, bpm) {
        if (loudness > 0.75) {
            this.transitionToTier(2);
            if (this.animeFx) this.animeFx.setEyeMode('star');
        } else if (loudness > 0.40) {
            this.breathingRate = 2.0 + (bpm / 60.0);
        }
    }

    triggerCursorStartle() {
        if (this.currentTier < 2) {
            this.transitionToTier(2);
        }
    }

    transitionToTier(newTier) {
        if (this.currentTier === newTier) {
            this.tierHoldTimer = 0.0;
            return;
        }

        if (newTier < this.currentTier) {
            if (this.tierHoldTimer < this.minHoldTime) return;
            if (this.activeSalience > this.hysteresisExitThreshold) return;
        }

        const oldTier = this.currentTier;
        this.currentTier = newTier;
        this.tierHoldTimer = 0.0;

        if (this.currentTier === 3) {
            if (this.chibiMod) this.chibiMod.enterChibi();
        } else if (oldTier === 3 && this.currentTier < 3) {
            if (this.chibiMod) this.chibiMod.exitChibi();
            if (this.animeFx) this.animeFx.resetAll();
        }

        if (this.onTierChange) {
            this.onTierChange(this.currentTier, oldTier);
        }
    }

    update(dt, continuousSalience) {
        this.activeSalience = Number(continuousSalience) || 0.0;
        this.tierHoldTimer += dt;
        this.breathingPhase += dt * this.breathingRate;

        if (this.currentTier === 3) {
            if (this.tierHoldTimer >= this.minHoldTime && this.activeSalience < this.hysteresisExitThreshold) {
                this.transitionToTier(this.activeSalience >= 0.40 ? 2 : 1);
            }
        } else if (this.currentTier === 2) {
            if (this.tierHoldTimer >= this.minHoldTime && this.activeSalience < 0.35) {
                this.transitionToTier(1);
            }
        }
    }

    getBreathingChestOffset() {
        return Math.sin(this.breathingPhase) * 0.015;
    }
}
