import * as THREE from 'three';

export class ChibiMorphModifier {
    constructor() {
        this.vrm = null;
        this.isChibi = false;
        this.morphProgress = 0.0;
        this.targetProgress = 0.0;
        this.morphSpeed = 4.5;
        this.originalBoneScales = new Map();
        this.headBones = [];
        this.torsoBones = [];
        this.limbBones = [];
    }

    setVrm(vrm) {
        this.vrm = vrm;
        this.originalBoneScales.clear();
        this.headBones = [];
        this.torsoBones = [];
        this.limbBones = [];
    }

    setEnabled(enable) {
        this.isChibi = false;
        this.targetProgress = 0.0;
    }

    enterChibi() {
        this.isChibi = false;
        this.targetProgress = 0.0;
    }

    exitChibi() {
        this.isChibi = false;
        this.targetProgress = 0.0;
    }

    toggleChibi() {
        this.isChibi = false;
        this.targetProgress = 0.0;
    }

    update(dt) {
    }

    _applyMorph(p) {
    }
}
