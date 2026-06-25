document.addEventListener("DOMContentLoaded", function () {
    // 1. Loading state for prompt-form (plan generator)
    const promptForm = document.querySelector(".prompt-form");
    if (promptForm) {
        promptForm.addEventListener("submit", function (e) {
            const submitBtn = promptForm.querySelector(".submit-btn");
            if (submitBtn) {
                // Get selected engine
                const engine = promptForm.querySelector("input[name='engine']:checked")?.value || "gemini";
                if (engine === "gemini") {
                    submitBtn.innerHTML = "✨ Drafting Plan with Wellness Assistant... Please wait... 🚀";
                } else {
                    submitBtn.innerHTML = "🧬 Running Genetic Portion Evolution Optimizer... 🧬";
                }
                submitBtn.disabled = true;
                submitBtn.style.opacity = "0.7";
                submitBtn.style.cursor = "not-allowed";
            }
        });
    }

    // 2. Loading state for profile-form
    const profileForm = document.querySelector(".profile-form");
    if (profileForm) {
        profileForm.addEventListener("submit", function () {
            const submitBtn = profileForm.querySelector(".submit-btn");
            if (submitBtn) {
                submitBtn.innerHTML = "💾 Saving wellness metrics & profiles... ⚙️";
                submitBtn.disabled = true;
                submitBtn.style.opacity = "0.7";
                submitBtn.style.cursor = "not-allowed";
            }
        });
    }
});
