/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useRef, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

/**
 * PdfFieldEditor — visual coordinate editor for clinic.billing.route.pdf.field.
 *
 * Renders the route's pdf_preview_image as a background and overlays a draggable
 * marker per field. Drag a marker to set (x, y) in PDF points; double-click a
 * marker to edit font_size via prompt. Changes are written immediately via ORM
 * (the parent record doesn't need to be saved).
 *
 * Coordinate space: PDF points (top-left origin). The preview image is rendered
 * at scale `pdf_preview_scale` (default 2.0 = 144 DPI); pixel = point * scale.
 */
export class PdfFieldEditor extends Component {
    static template = "clinic_core.PdfFieldEditor";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.canvasRef = useRef("canvas");
        this.state = useState({ draggingKey: null });
        this._boundMove = this.onMouseMove.bind(this);
        this._boundUp = this.onMouseUp.bind(this);
    }

    get previewUrl() {
        const recId = this.props.record.resId;
        if (!recId) return "";
        // Cache-bust by including write_date so freshly uploaded previews show up.
        return `/web/image?model=clinic.billing.route&id=${recId}&field=pdf_preview_image&unique=${recId}`;
    }

    get hasPreview() {
        return Boolean(this.props.record.data.pdf_preview_image);
    }

    get scale() {
        return this.props.record.data.pdf_preview_scale || 2.0;
    }

    get fields() {
        const list = this.props.record.data[this.props.name];
        return (list && list.records) ? list.records : [];
    }

    /** Key used to identify a marker (a record's resId or virtualId). */
    _keyOf(rec) {
        return rec.resId || rec._virtualId || rec.id || rec;
    }

    /** Inline style for a marker, in pixels. */
    markerStyle(rec) {
        const x = (rec.data.x || 0) * this.scale;
        const y = (rec.data.y || 0) * this.scale;
        const fs = rec.data.font_size || 9;
        return `left: ${x}px; top: ${y - fs}px; font-size: ${fs * this.scale * 0.9}px;`;
    }

    onMarkerMouseDown(ev, rec) {
        ev.preventDefault();
        ev.stopPropagation();
        this.state.draggingKey = this._keyOf(rec);
        this._draggedRec = rec;
        // Offset between the click point and the marker's top-left.
        const markerRect = ev.currentTarget.getBoundingClientRect();
        this._offsetPxX = ev.clientX - markerRect.left;
        this._offsetPxY = ev.clientY - markerRect.top;
        document.addEventListener("mousemove", this._boundMove);
        document.addEventListener("mouseup", this._boundUp);
    }

    onMouseMove(ev) {
        if (!this.state.draggingKey || !this._draggedRec) return;
        const canvas = this.canvasRef.el;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const newPxX = ev.clientX - rect.left - this._offsetPxX;
        const newPxY = ev.clientY - rect.top - this._offsetPxY;
        const fs = this._draggedRec.data.font_size || 9;
        // Top of marker in pixels -> top of text. Convert back to pt and re-add font_size
        // because we stored y as the text baseline-ish top.
        const newPtX = Math.max(0, newPxX / this.scale);
        const newPtY = Math.max(0, newPxY / this.scale) + fs;
        // Local update (re-renders marker live).
        this._draggedRec.update({ x: newPtX, y: newPtY });
    }

    async onMouseUp(ev) {
        const rec = this._draggedRec;
        this.state.draggingKey = null;
        this._draggedRec = null;
        document.removeEventListener("mousemove", this._boundMove);
        document.removeEventListener("mouseup", this._boundUp);
        if (rec && rec.resId) {
            await this.orm.write(
                "clinic.billing.route.pdf.field",
                [rec.resId],
                { x: rec.data.x, y: rec.data.y },
            );
        }
    }

    async onMarkerDoubleClick(ev, rec) {
        ev.preventDefault();
        ev.stopPropagation();
        const current = rec.data.font_size || 9;
        const input = window.prompt(
            `Tamaño de font para "${rec.data.label || rec.data.field_key}":`,
            String(current),
        );
        if (input == null) return;
        const parsed = parseInt(input, 10);
        if (!parsed || parsed < 4 || parsed > 72) return;
        rec.update({ font_size: parsed });
        if (rec.resId) {
            await this.orm.write(
                "clinic.billing.route.pdf.field",
                [rec.resId],
                { font_size: parsed },
            );
        }
    }
}

registry.category("fields").add("pdf_field_editor", {
    component: PdfFieldEditor,
    supportedTypes: ["one2many"],
    displayName: "Editor visual PDF",
});
