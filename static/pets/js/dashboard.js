(() => {
    "use strict";

    const dashboard = document.querySelector(".dashboard");
    if (!dashboard) return;

    const stateUrl = dashboard.dataset.stateUrl;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    const SPRITES = {
        egg: "🥚",
        baby: "🐥",
        teen: "🐤",
        adult: "🐔",
    };

    const SPRITE_MOOD = {
        happy: "😊",
        hungry: "🥺",
        sleepy: "😴",
        sad: "😢",
        dead: "💀",
    };

    function pickSprite(state) {
        if (!state.is_alive) return SPRITE_MOOD.dead;
        if (state.energy < 20) return SPRITE_MOOD.sleepy;
        if (state.hunger < 20) return SPRITE_MOOD.hungry;
        if (state.happiness < 20) return SPRITE_MOOD.sad;
        return SPRITES[state.stage] || SPRITES.baby;
    }

    function statusMessage(state) {
        if (!state.is_alive) return "Your pet has fainted. Be more attentive next time.";
        if (state.hunger < 20) return "Starving! Feed me!";
        if (state.energy < 20) return "So sleepy...";
        if (state.happiness < 20) return "Bored. Let's play!";
        if (state.overall > 80) return "Living the good life. ✨";
        return "Doing fine.";
    }

    function render(state) {
        document.querySelectorAll("[data-bind]").forEach(el => {
            const key = el.dataset.bind;
            if (key === "status") {
                el.textContent = statusMessage(state);
            } else if (state[key] !== undefined) {
                el.textContent = state[key];
            }
        });

        const setBar = (key, value, max) => {
            const el = document.querySelector(`[data-bar="${key}"]`);
            if (!el) return;
            const pct = Math.max(0, Math.min(100, (value / max) * 100));
            el.style.width = `${pct}%`;
        };
        setBar("hunger", state.hunger, 100);
        setBar("happiness", state.happiness, 100);
        setBar("energy", state.energy, 100);
        setBar("xp", state.xp, state.xp_to_next || 100);

        const sprite = document.querySelector("[data-bind-sprite]");
        if (sprite) sprite.textContent = pickSprite(state);

        document.querySelectorAll(".action-btn").forEach(btn => {
            btn.disabled = !state.is_alive;
        });
    }

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
        btn.classList.add("pulse");
        btn.disabled = true;
        try {
            const res = await fetch(url, {
                method: "POST",
                credentials: "same-origin",
                headers: { "X-CSRFToken": csrfToken },
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            render(await res.json());
        } catch (err) {
            console.error("action failed", err);
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

    // Initial render and lightweight polling for near-real-time updates.
    fetchState();
    setInterval(fetchState, 7000);
})();
