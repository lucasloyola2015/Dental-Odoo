(function () {
    "use strict";

    var token = document.body.dataset.token;
    var dniBox = document.getElementById("dni-display");
    var feedback = document.getElementById("feedback");
    var screenDni = document.getElementById("screen-dni");
    var screenSuccess = document.getElementById("screen-success");
    var successName = document.getElementById("success-name");
    var successInfo = document.getElementById("success-info");
    var countdown = document.getElementById("reset-countdown");
    var dni = "";

    function render() {
        if (dni.length === 0) {
            dniBox.textContent = "";
            dniBox.classList.add("empty");
        } else {
            dniBox.textContent = dni;
            dniBox.classList.remove("empty");
        }
    }

    function showFeedback(msg, kind) {
        feedback.textContent = msg;
        feedback.className = "feedback " + (kind || "info");
    }

    function clearFeedback() {
        feedback.textContent = "";
        feedback.className = "feedback hidden";
    }

    function postJson(url, payload) {
        return fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: payload || {} }),
        }).then(function (r) { return r.json(); }).then(function (j) { return j.result || {}; });
    }

    function resetToDni() {
        dni = "";
        render();
        clearFeedback();
        screenDni.classList.remove("hidden");
        screenSuccess.classList.add("hidden");
    }

    function formatCountdown(minutes) {
        if (minutes == null) return "";
        if (minutes < -5) {
            var late = -minutes;
            if (late < 60) return "Tu turno era hace " + late + " min.";
            return "Tu turno era hace " + Math.floor(late / 60) + "h " + (late % 60) + "m.";
        }
        if (minutes < 0) return "Tu turno era hace unos minutos. El profesional te llama enseguida.";
        if (minutes === 0) return "Es tu turno ahora.";
        if (minutes < 60) return "Faltan " + minutes + " minuto" + (minutes === 1 ? "" : "s") + " para tu turno.";
        var h = Math.floor(minutes / 60);
        var m = minutes % 60;
        if (m === 0) return "Faltan " + h + " hora" + (h === 1 ? "" : "s") + " para tu turno.";
        return "Faltan " + h + "h " + m + "m para tu turno.";
    }

    function showSuccess(res) {
        screenDni.classList.add("hidden");
        screenSuccess.classList.remove("hidden");
        successName.textContent = (res.patient || "") + (res.already_checked ? " (ya estabas registrado)" : "");
        var countdownText = formatCountdown(res.minutes_until);
        successInfo.innerHTML =
            '<div class="time">' + (res.time || "") + '</div>' +
            '<div class="practitioner">con ' + (res.practitioner || "") + '</div>' +
            (countdownText ? '<div class="countdown">' + countdownText + '</div>' : '');
        var n = 8;
        countdown.textContent = "Volviendo en " + n + "...";
        var iv = setInterval(function () {
            n -= 1;
            if (n <= 0) {
                clearInterval(iv);
                resetToDni();
            } else {
                countdown.textContent = "Volviendo en " + n + "...";
            }
        }, 1000);
    }

    function onSubmit() {
        if (!dni) { showFeedback("Ingresá tu DNI primero.", "error"); return; }
        showFeedback("Buscando turno...", "info");
        postJson("/kiosk/" + token + "/lookup", { token: token, dni: dni }).then(function (data) {
            if (data.error) { showFeedback(data.error, "error"); return; }
            if (!data.appointments || !data.appointments.length) {
                showFeedback("No encontramos turno para hoy.", "error");
                return;
            }
            // Prefer pending/booked; if none, the nearest (smallest abs minutes_until).
            var apt = data.appointments.find(function (a) {
                return a.state === "pending" || a.state === "booked";
            });
            if (!apt) {
                apt = data.appointments.slice().sort(function (a, b) {
                    return Math.abs(a.minutes_until) - Math.abs(b.minutes_until);
                })[0];
            }
            postJson("/kiosk/" + token + "/confirm", { token: token, appointment_id: apt.id }).then(function (res) {
                if (res.error) { showFeedback(res.error, "error"); return; }
                showSuccess(res);
            });
        }).catch(function () {
            showFeedback("Error de conexión. Avisá a la secretaría.", "error");
        });
    }

    Array.prototype.forEach.call(document.querySelectorAll("[data-digit]"), function (b) {
        b.addEventListener("click", function () {
            if (dni.length >= 12) return;
            dni += b.dataset.digit;
            render();
            clearFeedback();
        });
    });
    document.querySelector("[data-action=clear]").addEventListener("click", function () {
        dni = "";
        render();
        clearFeedback();
    });
    document.querySelector("[data-action=ok]").addEventListener("click", onSubmit);

    document.addEventListener("keydown", function (ev) {
        if (ev.key >= "0" && ev.key <= "9") {
            if (dni.length >= 12) return;
            dni += ev.key;
            render();
            clearFeedback();
        } else if (ev.key === "Backspace") {
            dni = dni.slice(0, -1);
            render();
        } else if (ev.key === "Enter") {
            onSubmit();
        } else if (ev.key === "Escape") {
            dni = "";
            render();
            clearFeedback();
        }
    });

    render();
})();
