(() => {
    "use strict";

    const dashboard = document.querySelector(".dashboard");
    if (!dashboard) return;

    const stateUrl = dashboard.dataset.stateUrl;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    const scene = document.getElementById("scene");
    const creature = scene.querySelector(".creature");
    const particles = document.getElementById("particles");
    const stars = document.getElementById("stars");

    let lastState = null;
    let animLock = false;

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

    function setMood(state) {
        creature.classList.remove("mood-hungry", "mood-sad", "mood-sleepy");
        if (!state.is_alive) return;
        if (state.energy < 25) creature.classList.add("mood-sleepy");
        else if (state.hunger < 25) creature.classList.add("mood-hungry");
        else if (state.happiness < 25) creature.classList.add("mood-sad");
    }

    function setTimeOfDay(state) {
        scene.classList.remove("dusk", "night");
        const hour = new Date().getHours();
        if (hour >= 20 || hour < 6) scene.classList.add("night");
        else if (hour >= 18) scene.classList.add("dusk");
    }

    function playActionAnim(name) {
        if (animLock) return;
        creature.classList.remove("eating", "playing", "sleeping");
        // Force reflow so re-adding a class restarts animation
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
            spawnParticle("Z", "zzz", 4);
        }
        setTimeout(() => {
            creature.classList.remove("eating", "playing");
            // keep .sleeping for a beat longer for visual rest
            animLock = false;
        }, 1700);
    }

    function statusMessage(state) {
        if (!state.is_alive) return "Your pet has fainted. Be more attentive next time.";
        if (state.hunger < 20) return "Starving! Feed me!";
        if (state.energy < 20) return "So sleepy...";
        if (state.happiness < 20) return "Bored. Let's play!";
        if (state.overall > 80) return "Living the good life. ✨";
        return "Doing fine.";
    }

    function showToast(text) {
        let toast = document.querySelector(".toast");
        if (!toast) {
            toast = document.createElement("div");
            toast.className = "toast";
            document.body.appendChild(toast);
        }
        toast.textContent = text;
        toast.classList.add("show");
        clearTimeout(toast._t);
        toast._t = setTimeout(() => toast.classList.remove("show"), 1800);
    }

    function diffMessage(prev, next) {
        const parts = [];
        if (next.xp > prev.xp) parts.push(`+${next.xp - prev.xp} XP`);
        if (next.coins > prev.coins) parts.push(`+${next.coins - prev.coins} 🪙`);
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
        setTimeOfDay(state);

        document.querySelectorAll(".action-btn").forEach(btn => {
            btn.disabled = !state.is_alive;
        });

        lastState = state;
    }

    /* ---------- Network ---------- */
    async function fetchState() {
        try {
            const res = await fetch(stateUrl, { credentials: "same-origin" });
            if (!res.ok) return;
            render(await res.json());
        } catch (err) {
            console.warn("state fetch failed", err);
        }
    }

    async function performAction(url, btn) {
        const actionName = btn.dataset.actionName;
        btn.classList.add("pulse");
        btn.disabled = true;
        playActionAnim(actionName);
        try {
            const res = await fetch(url, {
                method: "POST",
                credentials: "same-origin",
                headers: { "X-CSRFToken": csrfToken },
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const next = await res.json();
            if (lastState) {
                const msg = diffMessage(lastState, next);
                if (msg) showToast(msg);
                if (next.level > lastState.level) {
                    spawnParticle("✨", "spark", 6);
                }
            }
            render(next);
        } catch (err) {
            console.error("action failed", err);
            showToast("Something went wrong.");
        } finally {
            setTimeout(() => {
                btn.classList.remove("pulse");
                btn.disabled = false;
            }, 350);
        }
    }

    document.querySelectorAll(".action-btn").forEach(btn => {
        btn.addEventListener("click", () => performAction(btn.dataset.action, btn));
    });

    fetchState();
    setInterval(fetchState, 7000);
})();
