(() => {
    "use strict";

    const form = document.getElementById("upload-form");
    const videoInput = document.getElementById("video");
    const subtitleInput = document.getElementById("subtitle");
    const videoName = document.getElementById("video-file-name");
    const subtitleName = document.getElementById("subtitle-file-name");
    const confirmation = document.getElementById("selection-confirmation");
    const submitButton = document.getElementById("submit-button");
    const buttonLabel = document.getElementById("button-label");
    const progressArea = document.getElementById("progress-area");

    if (!form || !videoInput || !subtitleInput) return;

    function updateSelection() {
        videoName.textContent = videoInput.files.length
            ? videoInput.files[0].name
            : "No video selected";
        subtitleName.textContent = subtitleInput.files.length
            ? subtitleInput.files[0].name
            : "No subtitle selected";

        const complete = videoInput.files.length > 0 && subtitleInput.files.length > 0;
        confirmation.classList.toggle("hidden", !complete);
    }

    videoInput.addEventListener("change", updateSelection);
    subtitleInput.addEventListener("change", updateSelection);

    document.querySelectorAll(".upload-zone").forEach((zone) => {
        zone.addEventListener("dragover", (event) => {
            event.preventDefault();
            zone.classList.add("drag-active");
        });
        zone.addEventListener("dragleave", () => zone.classList.remove("drag-active"));
        zone.addEventListener("drop", () => zone.classList.remove("drag-active"));
    });

    form.addEventListener("submit", () => {
        submitButton.disabled = true;
        buttonLabel.textContent = "Uploading and analysing…";
        progressArea.classList.remove("hidden");
        const agentStep = document.getElementById("agent-step");

const steps = [
    "📤 Upload received...",
    "🎙️ Transcribing audio...",
    "📄 Parsing subtitles...",
    "🔍 Comparing subtitles with speech...",
    "🤖 AI reasoning...",
    "📋 Generating release assessment...",
    "✅ Finalizing report..."
];

let index = 0;

const interval = setInterval(() => {
    if (index < steps.length) {
        agentStep.textContent = steps[index];
        index++;
    } else {
        clearInterval(interval);
    }
}, 1500);
    });
})();
