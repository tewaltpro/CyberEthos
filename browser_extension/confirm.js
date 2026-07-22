const params = new URLSearchParams(window.location.search);
const downloadId = parseInt(params.get("id"), 10);
const fileName = params.get("name") || "this file";

document.getElementById("message").textContent =
  `Downloading "${fileName}". Sure you want to keep it?`;

document.getElementById("confirm").addEventListener("click", () => {
  chrome.downloads.resume(downloadId, () => window.close());
});

document.getElementById("cancel").addEventListener("click", () => {
  chrome.downloads.cancel(downloadId, () => window.close());
});
