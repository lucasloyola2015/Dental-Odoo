/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useEffect, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { OdontogramPopover } from "./odontogram_popover";

/**
 * OdontogramField — SVG odontogram with click-to-edit + table-edit sync.
 *
 * Renders the 52 FDI teeth in 4-quadrant layout. Each tooth has 5 surfaces
 * filled by (state, phase). Click a surface to open OdontogramPopover.
 *
 * Sync strategy:
 *   - localState.rows is the single source of truth for rendering.
 *   - useEffect watches a shallow hash of the parent record's O2m records and
 *     mirrors them into localState.rows. This catches BOTH user edits in the
 *     editable list below the SVG AND any record.load() triggered by the
 *     popover after a direct ORM write.
 *   - fdiByToothId map fills in tooth_fdi_code locally if the O2m record
 *     doesn't carry the related field (it isn't requested by the view).
 */
export class OdontogramField extends Component {
    static template = "clinic_dental.OdontogramField";
    static props = { ...standardFieldProps };

    static TOOTH_W = 36;
    static TOOTH_SPACING = 2;
    static MIDLINE_X = 380;

    static ROWS = [
        { y:  20, isUpper: true,  isDeciduous: true,
          right: [55, 54, 53, 52, 51], left: [61, 62, 63, 64, 65] },
        { y:  70, isUpper: true,  isDeciduous: false,
          right: [18, 17, 16, 15, 14, 13, 12, 11], left: [21, 22, 23, 24, 25, 26, 27, 28] },
        { y: 130, isUpper: false, isDeciduous: false,
          right: [48, 47, 46, 45, 44, 43, 42, 41], left: [31, 32, 33, 34, 35, 36, 37, 38] },
        { y: 180, isUpper: false, isDeciduous: true,
          right: [85, 84, 83, 82, 81], left: [71, 72, 73, 74, 75] },
    ];

    static COLOR = {
        planned: {
            caries: "#dc3545", restoration: "#dc3545", endodontic: "#dc3545",
            crown: "#dc3545", prosthesis: "#dc3545", implant: "#dc3545",
            extraction: "#dc3545", root_fragment: "#dc3545", missing: "#dc3545",
        },
        realized: {
            caries: "#6c757d", restoration: "#0d6efd", endodontic: "#0d6efd",
            crown: "#0d6efd", prosthesis: "#0d6efd", implant: "#0d6efd",
            extraction: "#0d6efd", root_fragment: "#6c757d", missing: "#0d6efd",
        },
    };

    setup() {
        this.orm = useService("orm");
        this.popover = usePopover(OdontogramPopover);
        this.fdiToToothId = {};
        this.fdiByToothId = {};
        this.localState = useState({ rows: [] });

        onWillStart(async () => {
            const teeth = await this.orm.searchRead(
                "clinic.dental.tooth", [], ["id", "fdi_code"]
            );
            for (const t of teeth) {
                this.fdiToToothId[t.fdi_code] = t.id;
                this.fdiByToothId[t.id] = t.fdi_code;
            }
        });

        // Mirror the parent O2m into localState whenever it changes.
        useEffect(
            () => { this._syncFromO2m(); },
            () => [this._o2mFingerprint()]
        );
    }

    /** Robustly extract a numeric id from a Many2one value (Odoo 19 may give array or object). */
    _extractToothId(toothIdValue) {
        if (toothIdValue == null) return null;
        if (Array.isArray(toothIdValue)) return toothIdValue[0] || null;
        if (typeof toothIdValue === "number") return toothIdValue;
        if (typeof toothIdValue === "object") {
            return toothIdValue.resId ?? toothIdValue.id ?? null;
        }
        return null;
    }

    /** Build a fingerprint string of the current O2m records so useEffect can detect changes. */
    _o2mFingerprint() {
        const list = this.props.record.data[this.props.name];
        const records = (list && list.records) ? list.records : [];
        return records.map(r => {
            const tid = this._extractToothId(r.data.tooth_id);
            return `${r.resId || "new"}|${tid}|${r.data.surface}|${r.data.phase}|${r.data.state}|${r.data.notes || ""}`;
        }).join("§");
    }

    _syncFromO2m() {
        const list = this.props.record.data[this.props.name];
        const records = (list && list.records) ? list.records : [];
        this.localState.rows = records.map(r => {
            let fdi = r.data.tooth_fdi_code;
            if (!fdi) {
                const toothId = this._extractToothId(r.data.tooth_id);
                if (toothId != null) {
                    fdi = this.fdiByToothId[toothId] || "";
                }
            }
            return {
                id: r.resId || null,
                tooth_fdi_code: fdi,
                surface: r.data.surface,
                phase: r.data.phase,
                state: r.data.state,
                notes: r.data.notes || "",
            };
        });
    }

    get topPath()    { return "M0,0 L36,0 L24,12 L12,12 Z"; }
    get rightPath()  { return "M36,0 L36,36 L24,24 L24,12 Z"; }
    get bottomPath() { return "M36,36 L0,36 L12,24 L24,24 Z"; }
    get leftPath()   { return "M0,36 L0,0 L12,12 L12,24 Z"; }

    get statesByTooth() {
        const map = {};
        for (const r of this.localState.rows) {
            const fdi = r.tooth_fdi_code;
            if (!fdi) continue;
            const surf = r.surface;
            if (!surf) continue;
            map[fdi] = map[fdi] || {};
            map[fdi][surf] = map[fdi][surf] || [];
            map[fdi][surf].push({ id: r.id, state: r.state, phase: r.phase, notes: r.notes });
        }
        return map;
    }

    fill(fdi, surface) {
        const states = (this.statesByTooth[fdi] || {})[surface] || [];
        const realized = states.find(s => s.phase === "realized");
        const planned  = states.find(s => s.phase === "planned");
        if (realized) return OdontogramField.COLOR.realized[realized.state] || "#999";
        if (planned)  return OdontogramField.COLOR.planned[planned.state]   || "#dc3545";
        return "#ffffff";
    }

    tooltip(fdi, surface) {
        const states = (this.statesByTooth[fdi] || {})[surface] || [];
        if (!states.length) return `${fdi} · ${surface} (click para registrar)`;
        const parts = states.map(s => `${s.state} (${s.phase === "planned" ? "previsto" : "realizado"})`);
        return `${fdi} · ${surface}: ${parts.join(" + ")}`;
    }

    get positionedTeeth() {
        const items = [];
        const W = OdontogramField.TOOTH_W;
        const S = OdontogramField.TOOTH_SPACING;
        const M = OdontogramField.MIDLINE_X;
        for (const row of OdontogramField.ROWS) {
            row.right.forEach((fdi, i) => {
                const x = M - (i + 1) * (W + S);
                items.push(this._buildTooth(fdi, x, row));
            });
            row.left.forEach((fdi, i) => {
                const x = M + i * (W + S) + S;
                items.push(this._buildTooth(fdi, x, row));
            });
        }
        return items;
    }

    _buildTooth(fdi, x, row) {
        const topSurface    = row.isUpper ? "buccal"  : "lingual";
        const bottomSurface = row.isUpper ? "lingual" : "buccal";
        const inLeftHalf = row.left.includes(fdi);
        const leftSurface  = inLeftHalf ? "distal" : "mesial";
        const rightSurface = inLeftHalf ? "mesial" : "distal";
        const labelY = row.isUpper ? -4 : 50;
        return {
            fdi: String(fdi),
            transform: `translate(${x}, ${row.y})`,
            labelY: labelY,
            surfaceTop: topSurface, surfaceRight: rightSurface,
            surfaceBottom: bottomSurface, surfaceLeft: leftSurface,
            fillTop:    this.fill(fdi, topSurface),
            fillRight:  this.fill(fdi, rightSurface),
            fillBottom: this.fill(fdi, bottomSurface),
            fillLeft:   this.fill(fdi, leftSurface),
            fillCenter: this.fill(fdi, "occlusal"),
            tooltipTop:    this.tooltip(fdi, topSurface),
            tooltipRight:  this.tooltip(fdi, rightSurface),
            tooltipBottom: this.tooltip(fdi, bottomSurface),
            tooltipLeft:   this.tooltip(fdi, leftSurface),
            tooltipCenter: this.tooltip(fdi, "occlusal"),
        };
    }

    async onSurfaceClick(ev, fdi, surface) {
        ev.stopPropagation();
        const patientId = this.props.record.resId;
        if (!patientId) return;
        const toothId = this.fdiToToothId[fdi];
        if (!toothId) return;
        const existing = (this.statesByTooth[fdi] || {})[surface] || [];
        this.popover.open(ev.currentTarget, {
            fdi: String(fdi),
            surface,
            patientId,
            toothId,
            existing,
            onChange: async () => {
                // Reload parent record -> useEffect picks up the new O2m records.
                await this.props.record.load();
            },
        });
    }
}

registry.category("fields").add("odontogram", {
    component: OdontogramField,
    supportedTypes: ["one2many"],
    displayName: "Odontograma",
});
