(() => {
    "use strict";

    const dashboard = document.querySelector(".dashboard");
    if (!dashboard) return;

    const stateUrl = dashboard.dataset.stateUrl;
    const renameUrl = dashboard.dataset.renameUrl;
    const healUrl = dashboard.dataset.healUrl;
    const medicineUrl = dashboard.dataset.medicineUrl;
    const recolorUrl = dashboard.dataset.recolorUrl;
    const achievementsUrl = dashboard.dataset.achievementsUrl;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    const scene = document.getElementById("scene");
    const creature = scene.querySelector(".creature");
    const particles = document.getElementById("particles");
    const stars = document.getElementById("stars");
    const healBtn = document.getElementById("heal-btn");
    const medicineBtn = document.getElementById("medicine-btn");
    const achievementList = document.getElementById("achievement-list");

    let lastState = null;
    let animLock = false;
    let pollTimer = null;
    const POLL_MS = 7000;

    /* Mouth path strings keyed by expression. Applied via setAttribute
       so we do not depend on CSS support for the SVG `d` property. */
    const MOUTH_PATHS = {
        happy:  "M 95 178 Q 110 192 125 178",
        sad:    "M 95 188 Q 110 178 125 188",
        hungry: "M 95 184 Q 110 174 125 184",
        sleep:  "M 100 184 Q 110 188 120 184",
    };
    const mouth = creature.querySelector(".mouth");
    const eyes = creature.querySelectorAll(".eye");

    function setMouth(key) {
        if (mouth && MOUTH_PATHS[key]) mouth.setAttribute("d", MOUTH_PATHS[key]);
    }
    function setEyeRy(value) {
        eyes.forEach(e => e.setAttribute("ry", value));
    }

    /* ---------- One-time scene setup ---------- */
    function spawnStars(count = 40) {
        for (let i = 0; i < count; i++) {
            const s = document.createElement("div");
            s.className = "star";
            s.style.left = `${Math.random() * 100}%`;
            s.style.top = `${Math.random() * 60}%`;
            s.style.animationDelay = `${Math.random() * 3}s`;
            stars.appendChild(s);
        }
    }
    spawnStars();

    /* ---------- Particle factory ---------- */
    function spawnParticle(text, klass, count = 1) {
        for (let i = 0; i < count; i++) {
            const p = document.createElement("div");
            p.className = `particle ${klass}`;
            p.textContent = text;
            const dx = (Math.random() - 0.5) * 80;
            p.style.setProperty("--dx", `${dx}px`);
            p.style.animationDelay = `${i * 0.12}s`;
            particles.appendChild(p);
            setTimeout(() => p.remove(), 1800 + i * 120);
        }
    }

    /* ---------- Sprite state machine ---------- */
    function setStage(stage) {
        creature.classList.remove("egg", "baby", "teen", "adult");
        creature.classList.add(stage);
    }

    function setColor(color) {
        creature.classList.remove("color-pink", "color-blue", "color-mint", "color-lavender", "color-gold");
        creature.classList.add(`color-${color}`);
        document.querySelectorAll(".swatch").forEach(s => {
            s.classList.toggle("active", s.dataset.color === color);
        });
    }

    function setSick(isSick) {
        creature.classList.toggle("sick", !!isSick);
    }

    function setMood(state) {
        creature.classList.remove("mood-hungry", "mood-sad", "mood-sleepy");
        setEyeRy(14);
        if (!state.is_alive) {
            setMouth("sad");
            return;
        }
        if (state.energy < 25) {
            creature.classList.add("mood-sleepy");
            setMouth("happy");
        } else if (state.hunger < 25) {
            creature.classList.add("mood-hungry");
            setMouth("hungry");
        } else if (state.happiness < 25) {
            creature.classList.add("mood-sad");
            setMouth("sad");
            setEyeRy(10);
        } else {
            setMouth("happy");
        }
    }

    function setTimeOfDay() {
        scene.classList.remove("dusk", "night");
        const hour = new Date().getHours();
        if (hour >= 20 || hour < 6) scene.classList.add("night");
        else if (hour >= 18) scene.classList.add("dusk");
    }

    function playActionAnim(name) {
        if (animLock) return;
        creature.classList.remove("eating", "playing", "sleeping");
        void creature.offsetWidth;
        animLock = true;
        if (name === "feed") {
            creature.classList.add("eating");
            spawnParticle("🍞", "crumb", 4);
        } else if (name === "play") {
            creature.classList.add("playing");
            spawnParticle("❤️", "heart", 5);
        } else if (name === "sleep") {
            creature.classList.add("sleeping");
            setMouth("sleep");
            spawnParticle("Z", "zzz", 4);
        } else if (name === "heal") {
            spawnParticle("✨", "spark", 8);
        } else if (name === "fetch") {
            creature.classList.add("playing");
            spawnParticle("🥏", "heart", 6);
        } else if (name === "medicine") {
            spawnParticle("💚", "spark", 6);
        }
        setTimeout(() => {
            creature.classList.remove("eating", "playing", "sleeping");
            if (lastState) setMood(lastState);
            animLock = false;
        }, 1700);
    }

    function statusMessage(state) {
        if (!state.is_alive) return "Your pet has fainted. Heal it to bring it back.";
        if (state.is_sick) return "Sniffles. Some medicine would help...";
        if (state.hunger < 20) return "Starving! Feed me!";
        if (state.energy < 20) return "So sleepy...";
        if (state.happiness < 20) return "Bored. Let's play!";
        if (state.overall > 80) return "Living the good life. ✨";
        return "Doing fine.";
    }

    function showToast(text, duration = 1800) {
        let toast = document.querySelector(".toast");
        if (!toast) {
            toast = document.createElement("div");
            toast.className = "toast";
            document.body.appendChild(toast);
        }
        toast.textContent = text;
        toast.classList.add("show");
        clearTimeout(toast._t);
        toast._t = setTimeout(() => toast.classList.remove("show"), duration);
    }

    function diffMessage(prev, next) {
        const parts = [];
        if (next.xp > prev.xp) parts.push(`+${next.xp - prev.xp} XP`);
        if (next.coins !== prev.coins) {
            const delta = next.coins - prev.coins;
            parts.push(`${delta >= 0 ? "+" : ""}${delta} 🪙`);
        }
        if (next.level > prev.level) parts.push(`Level up! ${next.level}`);
        if (next.stage !== prev.stage) parts.push(`Evolved → ${next.stage}!`);
        return parts.join("  ·  ");
    }

    /* ---------- Render ---------- */
    function render(state) {
        document.querySelectorAll("[data-bind]").forEach(el => {
            const key = el.dataset.bind;
            if (key === "status") el.textContent = statusMessage(state);
            else if (state[key] !== undefined) el.textContent = state[key];
        });

        const setBar = (key, value, max) => {
            const el = document.querySelector(`[data-bar="${key}"]`);
            if (el) el.style.width = `${Math.max(0, Math.min(100, (value / max) * 100))}%`;
        };
        setBar("hunger", state.hunger, 100);
        setBar("happiness", state.happiness, 100);
        setBar("energy", state.energy, 100);
        setBar("xp", state.xp, state.xp_to_next || 100);

        if (lastState && lastState.stage !== state.stage) {
            scene.classList.add("hatch-flash");
            setTimeout(() => scene.classList.remove("hatch-flash"), 800);
        }

        setStage(state.stage);
        setMood(state);
        setTimeOfDay();
        if (state.color) setColor(state.color);
        setSick(state.is_sick);

        // Heal button visibility: show when fainted or any stat below 20.
        const needsHeal = !state.is_alive
            || state.hunger < 20 || state.happiness < 20 || state.energy < 20;
        healBtn.hidden = !needsHeal;
        healBtn.disabled = state.coins < state.heal_cost;

        // Medicine button: only when sick.
        medicineBtn.hidden = !state.is_sick;
        medicineBtn.disabled = state.coins < (state.medicine_cost || 8);

        document.querySelectorAll(".action-btn").forEach(btn => {
            btn.disabled = !state.is_alive;
        });

        // Notify when stats first cross the worry threshold (browser
        // notification, opt-in only). Compares against the previous
        // state so we do not spam every poll.
        maybeNotify(state);

        // Pop a celebratory toast for any achievements just unlocked.
        if (state.new_achievements && state.new_achievements.length) {
            state.new_achievements.forEach(a => {
                showToast(`${a.icon}  Achievement: ${a.name}`, 3500);
                spawnParticle("🏆", "spark", 6);
            });
            // Re-fetch the list so the tray updates.
            fetchAchievements();
        }

        lastState = state;
    }

    /* ---------- Network ---------- */
    async function fetchState() {
        if (document.hidden) return;  // pause polling when tab is hidden
        try {
            const res = await fetch(stateUrl, { credentials: "same-origin" });
            if (!res.ok) return;
            render(await res.json());
        } catch (err) {
            console.warn("state fetch failed", err);
        }
    }

    function startPolling() {
        stopPolling();
        pollTimer = setInterval(fetchState, POLL_MS);
    }
    function stopPolling() {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    }

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            stopPolling();
        } else {
            fetchState();
            startPolling();
        }
    });

    async function performAction(url, btn, actionName) {
        btn.classList.add("pulse");
        btn.disabled = true;
        playActionAnim(actionName);
        try {
            const res = await fetch(url, {
                method: "POST",
                credentials: "same-origin",
                headers: { "X-CSRFToken": csrfToken },
            });
            if (res.status === 429) {
                showToast("Slow down a little! 🐢");
                return;
            }
            if (res.status === 402) {
                showToast("Not enough coins.");
                return;
            }
            if (res.status === 409) {
                const body = await res.json().catch(() => ({}));
                if (body.error === "too_tired") showToast("Too tired for fetch.");
                else if (body.error === "not_sick") showToast("Pet is not sick.");
                else showToast("Can't do that right now.");
                return;
            }
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const next = await res.json();
            if (lastState) {
                const msg = diffMessage(lastState, next);
                if (msg) {
                    const isLevelUp = next.level > lastState.level || next.stage !== lastState.stage;
                    showToast(msg, isLevelUp ? 3500 : 1800);
                }
                if (next.level > lastState.level) {
                    spawnParticle("✨", "spark", 8);
                }
            }
            render(next);
        } catch (err) {
            console.error("action failed", err);
            showToast("Something went wrong.");
        } finally {
            setTimeout(() => {
                btn.classList.remove("pulse");
                btn.disabled = !lastState || !lastState.is_alive;
            }, 350);
        }
    }

    document.querySelectorAll(".action-btn").forEach(btn => {
        btn.addEventListener("click", () => performAction(btn.dataset.action, btn, btn.dataset.actionName));
    });

    healBtn.addEventListener("click", () => performAction(healUrl, healBtn, "heal"));
    medicineBtn.addEventListener("click", () => performAction(medicineUrl, medicineBtn, "medicine"));

    /* ---------- Color picker ---------- */
    document.querySelectorAll(".swatch").forEach(swatch => {
        swatch.addEventListener("click", async () => {
            const color = swatch.dataset.color;
            try {
                const res = await fetch(recolorUrl, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ color }),
                });
                if (res.ok) render(await res.json());
                else if (res.status === 429) showToast("Too many color changes.");
            } catch (err) {
                console.error(err);
            }
        });
    });

    /* ---------- Achievements ---------- */
    async function fetchAchievements() {
        try {
            const res = await fetch(achievementsUrl, { credentials: "same-origin" });
            if (!res.ok) return;
            const data = await res.json();
            renderAchievements(data.achievements || []);
        } catch (err) {
            console.warn("achievements fetch failed", err);
        }
    }

    function renderAchievements(list) {
        if (!achievementList) return;
        achievementList.innerHTML = list.map(a => `
            <li class="${a.unlocked ? "unlocked" : ""}" title="${a.description}">
                <span class="ach-icon">${a.icon}</span>
                <span><span class="ach-name">${a.name}</span><span class="ach-desc">${a.description}</span></span>
            </li>
        `).join("");
    }

    /* ---------- Browser notifications for low stats ---------- */
    // Only fire once per stat-becomes-low transition, not every poll.
    const NOTIFY_THRESHOLD = 20;
    function maybeNotify(state) {
        if (!("Notification" in window)) return;
        if (Notification.permission !== "granted") return;
        if (!lastState || !state.is_alive) return;
        const stats = ["hunger", "happiness", "energy"];
        for (const k of stats) {
            if (state[k] < NOTIFY_THRESHOLD && lastState[k] >= NOTIFY_THRESHOLD) {
                const labels = { hunger: "hungry", happiness: "bored", energy: "sleepy" };
                new Notification(`${state.name} is ${labels[k]}`, {
                    body: "Drop in and check on your pet.",
                    icon: "/static/favicon.svg",
                    tag: `nosypet-${k}`,
                });
            }
        }
    }

    // Ask once, after first user interaction, so we are not blocked
    // by the autoplay-style permission heuristics.
    let askedNotify = false;
    function askNotifyOnce() {
        if (askedNotify) return;
        askedNotify = true;
        if ("Notification" in window && Notification.permission === "default") {
            Notification.requestPermission().catch(() => {});
        }
    }
    document.querySelectorAll(".action-btn").forEach(btn => {
        btn.addEventListener("click", askNotifyOnce, { once: true });
    });

    /* ---------- Rename dialog ---------- */
    const dialog = document.getElementById("rename-dialog");
    const renameInput = document.getElementById("rename-input");
    const renameCancel = document.getElementById("rename-cancel");

    document.querySelector(".name-edit").addEventListener("click", () => {
        renameInput.value = lastState ? lastState.name : "";
        if (typeof dialog.showModal === "function") dialog.showModal();
        renameInput.focus();
        renameInput.select();
    });
    renameCancel.addEventListener("click", () => dialog.close());

    document.getElementById("rename-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const name = renameInput.value.trim();
        if (!name) return;
        try {
            const res = await fetch(renameUrl, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ name }),
            });
            if (res.ok) {
                render(await res.json());
                dialog.close();
                showToast("Name updated.");
            } else if (res.status === 429) {
                showToast("Too many rename attempts.");
            } else {
                showToast("Invalid name.");
            }
        } catch (err) {
            console.error(err);
            showToast("Something went wrong.");
        }
    });

    /* ---------- Boot ---------- */
    fetchState();
    fetchAchievements();
    startPolling();

    // Register PWA service worker if available.
    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
})();
