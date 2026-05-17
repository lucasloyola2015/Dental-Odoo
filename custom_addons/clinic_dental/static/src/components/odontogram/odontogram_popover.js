/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const STATE_OPTIONS = [
    ["caries",        "Caries"],
    ["restoration",   "Obturación"],
    ["endodontic",    "Endodoncia"],
    ["crown",         "Corona"],
    ["prosthesis",    "Prótesis"],
    ["implant",       "Implante"],
    ["extraction",    "Extracción / Ausente"],
    ["root_fragment", "Resto radicular"],
    ["missing",       "Ausente (no erupcionó)"],
];

const PHASE_OPTIONS = [
    ["planned",  "Previsto / observado (rojo)"],
    ["realized", "Realizado / existente (azul)"],
];

const SURFACE_LABELS = {
    occlusal: "Oclusal / Incisal",
    mesial:   "Mesial",
    distal:   "Distal",
    buccal:   "Vestibular",
    lingual:  "Lingual / Palatino",
};

/**
 * OdontogramPopover — popover for editing one (tooth, surface) on the odontogram.
 *
 * Props:
 *  - close:        callback to close the popover (provided by popover service)
 *  - fdi:          FDI code of the tooth (string)
 *  - surface:      anatomical surface ("occlusal" / "mesial" / ...)
 *  - patientId:    clinic.patient id (required to write back)
 *  - toothId:      clinic.dental.tooth id (required to create)
 *  - existing:     array of existing state records for this surface (may be 0..2)
 *  - onChange:     async callback fired after a successful save/delete (parent reloads)
 */
export class OdontogramPopover extends Component {
    static template = "clinic_dental.OdontogramPopover";
    static props = {
        close: Function,
        fdi: String,
        surface: String,
        patientId: Number,
        toothId: Number,
        existing: Array,
        onChange: Function,
    };

    setup() {
        this.orm = useService("orm");

        // Determine which phase we are editing: default planned, or pick the
        // first existing record's phase if any.
        const initialPhase = this.props.existing[0]?.phase || "planned";
        const matching = this.props.existing.find(r => r.phase === initialPhase);

        this.state = useState({
            phase: initialPhase,
            stateValue: matching?.state || "caries",
            notes: matching?.notes || "",
            saving: false,
        });
    }

    get stateOptions()   { return STATE_OPTIONS; }
    get phaseOptions()   { return PHASE_OPTIONS; }
    get surfaceLabel()   { return SURFACE_LABELS[this.props.surface] || this.props.surface; }

    /** Existing record for the currently selected phase, if any. */
    get matchingExisting() {
        return this.props.existing.find(r => r.phase === this.state.phase);
    }

    /** Sync stateValue/notes when the user switches phase via the dropdown. */
    onPhaseChange(ev) {
        const newPhase = ev.target.value;
        this.state.phase = newPhase;
        const m = this.props.existing.find(r => r.phase === newPhase);
        this.state.stateValue = m?.state || "caries";
        this.state.notes = m?.notes || "";
    }

    async save() {
        if (this.state.saving) return;
        this.state.saving = true;
        try {
            const existing = this.matchingExisting;
            const vals = {
                state: this.state.stateValue,
                notes: this.state.notes,
            };
            if (existing) {
                await this.orm.write("clinic.dental.tooth.state", [existing.id], vals);
            } else {
                await this.orm.create("clinic.dental.tooth.state", [{
                    ...vals,
                    patient_id: this.props.patientId,
                    tooth_id:   this.props.toothId,
                    surface:    this.props.surface,
                    phase:      this.state.phase,
                }]);
            }
            await this.props.onChange();
            this.props.close();
        } finally {
            this.state.saving = false;
        }
    }

    async remove() {
        if (this.state.saving) return;
        const existing = this.matchingExisting;
        if (!existing) {
            this.props.close();
            return;
        }
        this.state.saving = true;
        try {
            await this.orm.unlink("clinic.dental.tooth.state", [existing.id]);
            await this.props.onChange();
            this.props.close();
        } finally {
            this.state.saving = false;
        }
    }
}
