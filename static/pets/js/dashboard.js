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

        lastState = state;
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

    function playSpriteAnim(actionName) {
        const sprite = document.querySelector("[data-bind-sprite]");
        if (!sprite) return;
        const klass = { feed: "eat", play: "play", sleep: "sleep" }[actionName];
        if (!klass) return;
        sprite.classList.remove("eat", "play", "sleep");
        void sprite.offsetWidth;
        sprite.classList.add(klass);
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
        return parts.join("  ·  ");
    }

    let lastState = null;

    async function performAction(url, btn) {
        const actionName = btn.dataset.actionName || (url.match(/\/(feed|play|sleep)\//) || [])[1];
        btn.classList.add("pulse");
        btn.disabled = true;
        playSpriteAnim(actionName);
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

    // Initial render and lightweight polling for near-real-time updates.
    fetchState();
    setInterval(fetchState, 7000);
})();
