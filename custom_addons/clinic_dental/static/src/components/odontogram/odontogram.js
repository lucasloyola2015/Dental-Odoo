/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * OdontogramField — read-only SVG odontogram widget.
 *
 * Field widget for a One2many to clinic.dental.tooth.state. Renders the
 * 52 FDI teeth (32 permanent + 20 deciduous) in the classical 4-quadrant
 * layout with deciduous nested inside permanent. Each tooth has 5 clickable
 * surfaces; surfaces are filled with a color derived from (state, phase).
 *
 * Iteration B = read-only display. Iteration C will add edit-from-SVG.
 */
export class OdontogramField extends Component {
    static template = "clinic_dental.OdontogramField";
    static props = { ...standardFieldProps };

    setup() {
        // No reactive state needed for iteration B.
    }

    // --- Layout (rows, left half then right half of mouth) ---
    static UPPER_PERM = {
        right: [18, 17, 16, 15, 14, 13, 12, 11],
        left:  [21, 22, 23, 24, 25, 26, 27, 28],
    };
    static UPPER_TEMP = {
        right: [55, 54, 53, 52, 51],
        left:  [61, 62, 63, 64, 65],
    };
    static LOWER_PERM = {
        right: [48, 47, 46, 45, 44, 43, 42, 41],
        left:  [31, 32, 33, 34, 35, 36, 37, 38],
    };
    static LOWER_TEMP = {
        right: [85, 84, 83, 82, 81],
        left:  [71, 72, 73, 74, 75],
    };

    static SURFACES = ["occlusal", "mesial", "distal", "buccal", "lingual"];

    // (state, phase) -> CSS fill color. Red family = planned; Blue family = realized.
    static COLOR_MAP = {
        planned: {
            caries:        "#dc3545",  // red
            restoration:   "#dc3545",
            endodontic:    "#dc3545",
            crown:         "#dc3545",
            prosthesis:    "#dc3545",
            implant:       "#dc3545",
            extraction:    "#dc3545",
            root_fragment: "#dc3545",
            missing:       "#dc3545",
        },
        realized: {
            caries:        "#6c757d",  // gray (rare: untreated caries observed historically)
            restoration:   "#0d6efd",  // blue
            endodontic:    "#0d6efd",
            crown:         "#0d6efd",
            prosthesis:    "#0d6efd",
            implant:       "#0d6efd",
            extraction:    "#0d6efd",
            root_fragment: "#6c757d",
            missing:       "#0d6efd",
        },
    };

    /**
     * Build a lookup: { fdi_code: { surface: [stateRecord, ...] } }
     * Both phases for the same surface are stored, planned first.
     */
    get statesByTooth() {
        const records = this.props.record.data[this.props.name].records;
        const map = {};
        for (const r of records) {
            const fdi = r.data.tooth_fdi_code;
            if (!fdi) continue;
            if (!map[fdi]) map[fdi] = {};
            const surf = r.data.surface;
            if (!map[fdi][surf]) map[fdi][surf] = [];
            map[fdi][surf].push({
                state: r.data.state,
                phase: r.data.phase,
                notes: r.data.notes || "",
            });
        }
        return map;
    }

    /**
     * Return the fill color for a (fdi, surface) cell. If both planned and
     * realized exist for the same surface, realized takes precedence visually
     * (it represents the most recent fact about the surface).
     */
    surfaceFill(fdi, surface) {
        const states = (this.statesByTooth[fdi] || {})[surface] || [];
        const realized = states.find(s => s.phase === "realized");
        const planned  = states.find(s => s.phase === "planned");
        if (realized) return OdontogramField.COLOR_MAP.realized[realized.state] || "#999";
        if (planned)  return OdontogramField.COLOR_MAP.planned[planned.state]   || "#dc3545";
        return "#ffffff";
    }

    /** Tooltip text for a (fdi, surface) cell. */
    surfaceTooltip(fdi, surface) {
        const states = (this.statesByTooth[fdi] || {})[surface] || [];
        if (!states.length) return `${fdi} · ${surface}`;
        const parts = states.map(s => `${s.state} (${s.phase === "planned" ? "previsto" : "realizado"})`);
        return `${fdi} · ${surface}: ${parts.join(" + ")}`;
    }

    /** Helper used by the template iteration: gives x-position of a tooth in its row. */
    toothX(index, options = {}) {
        const TOOTH_W = 36;
        const SPACING = 2;
        const offset = options.offsetCenter ? (3 * (TOOTH_W + SPACING)) : 0;
        return index * (TOOTH_W + SPACING) + offset;
    }

    /** Provide rows to the template in order. */
    get rows() {
        return [
            { y: 5,   teeth: OdontogramField.UPPER_TEMP.right, offsetCenter: true,  label: "Temp. sup. der." },
            { y: 5,   teeth: OdontogramField.UPPER_TEMP.left,  offsetCenter: true,  label: "Temp. sup. izq.", side: "left" },
            { y: 55,  teeth: OdontogramField.UPPER_PERM.right, offsetCenter: false, label: "Perm. sup. der." },
            { y: 55,  teeth: OdontogramField.UPPER_PERM.left,  offsetCenter: false, label: "Perm. sup. izq.", side: "left" },
            { y: 110, teeth: OdontogramField.LOWER_PERM.right, offsetCenter: false, label: "Perm. inf. der." },
            { y: 110, teeth: OdontogramField.LOWER_PERM.left,  offsetCenter: false, label: "Perm. inf. izq.", side: "left" },
            { y: 160, teeth: OdontogramField.LOWER_TEMP.right, offsetCenter: true,  label: "Temp. inf. der." },
            { y: 160, teeth: OdontogramField.LOWER_TEMP.left,  offsetCenter: true,  label: "Temp. inf. izq.", side: "left" },
        ];
    }
}

registry.category("fields").add("odontogram", {
    component: OdontogramField,
    supportedTypes: ["one2many"],
    displayName: "Odontograma",
});
