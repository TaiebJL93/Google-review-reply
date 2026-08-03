document.addEventListener("click", async (event) => {
  const draftButton = event.target.closest("[data-draft-review-id]");
  if (draftButton) {
    await handleDraft(draftButton);
    return;
  }

  const copyButton = event.target.closest("[data-copy-target]");
  if (copyButton) {
    handleCopy(copyButton);
  }
});

async function handleDraft(button) {
  const reviewId = button.getAttribute("data-draft-review-id");
  const container = document.getElementById(`draft-${reviewId}`);
  const originalLabel = button.textContent;

  button.disabled = true;
  button.textContent = "Drafting...";

  try {
    const response = await fetch(`/reviews/${reviewId}/draft`, { method: "POST" });
    if (!response.ok) {
      const message = await readErrorMessage(response);
      showError(container, message);
      return;
    }
    container.innerHTML = await response.text();
  } catch (err) {
    showError(container, "Network error — please try again.");
  } finally {
    button.disabled = false;
    button.textContent = originalLabel;
  }
}

async function readErrorMessage(response) {
  try {
    const data = await response.json();
    return data.detail || "Something went wrong.";
  } catch (err) {
    return "Something went wrong.";
  }
}

function showError(container, message) {
  container.innerHTML = "";
  const p = document.createElement("p");
  p.className = "error";
  p.textContent = message;
  container.appendChild(p);
}

async function handleCopy(button) {
  const targetId = button.getAttribute("data-copy-target");
  const textarea = document.getElementById(targetId);
  if (!textarea) return;

  await navigator.clipboard.writeText(textarea.value);
  const original = button.textContent;
  button.textContent = "Copied!";
  setTimeout(() => { button.textContent = original; }, 1500);
}
