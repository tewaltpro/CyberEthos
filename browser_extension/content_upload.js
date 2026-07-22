// CyberEthos Reflect - upload interception
// Intercepts clicks that would open a file picker (input[type=file], or
// elements that trigger one via JS) and shows a brief reflection prompt
// first. If the user confirms, we replay the click so the picker opens.

(function () {
  const PROMPT_TEXT = "If this file were on the news tomorrow, how would you feel?";
  let bypassNextClick = false;

  function isFileInput(el) {
    return el && el.tagName === "INPUT" && el.type === "file";
  }

  function showReflectionModal(onConfirm) {
    if (document.getElementById("cyberethos-modal-overlay")) return;

    const overlay = document.createElement("div");
    overlay.id = "cyberethos-modal-overlay";
    overlay.style.cssText = `
      position: fixed; inset: 0; background: rgba(10,10,20,0.75);
      z-index: 2147483647; display: flex; align-items: center;
      justify-content: center; font-family: 'Segoe UI', sans-serif;
    `;

    const box = document.createElement("div");
    box.style.cssText = `
      background: #1b1b2f; color: #eaeaf0; padding: 28px 32px;
      border-radius: 12px; max-width: 380px; text-align: center;
      box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    `;
    box.innerHTML = `
      <div style="font-size:15px; line-height:1.5; margin-bottom:20px;">
        ${PROMPT_TEXT}
      </div>
    `;

    const proceedBtn = document.createElement("button");
    proceedBtn.textContent = "Yes, continue";
    proceedBtn.style.cssText = `
      background:#0f3460; color:white; border:none; padding:10px 18px;
      border-radius:8px; margin-right:10px; cursor:pointer; font-size:14px;
    `;

    const cancelBtn = document.createElement("button");
    cancelBtn.textContent = "Not yet";
    cancelBtn.style.cssText = `
      background:#333; color:white; border:none; padding:10px 18px;
      border-radius:8px; cursor:pointer; font-size:14px;
    `;

    proceedBtn.onclick = () => {
      overlay.remove();
      onConfirm();
    };
    cancelBtn.onclick = () => overlay.remove();

    box.appendChild(document.createElement("br"));
    box.appendChild(proceedBtn);
    box.appendChild(cancelBtn);
    overlay.appendChild(box);
    document.documentElement.appendChild(overlay);
  }

  document.addEventListener(
    "click",
    function (event) {
      if (bypassNextClick) {
        bypassNextClick = false;
        return; // let our own replayed click through
      }
      const target = event.target;
      if (isFileInput(target)) {
        event.preventDefault();
        event.stopPropagation();
        showReflectionModal(() => {
          bypassNextClick = true;
          target.click();
        });
      }
    },
    true // capture phase, so we intercept before the picker opens
  );
})();
