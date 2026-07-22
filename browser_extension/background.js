// CyberEthos Reflect - download interception
// Pauses new downloads immediately, opens a small confirmation popup,
// then resumes or cancels based on the user's choice.

chrome.downloads.onCreated.addListener((downloadItem) => {
  chrome.downloads.pause(downloadItem.id, () => {
    chrome.windows.create({
      url: chrome.runtime.getURL(
        `confirm.html?id=${downloadItem.id}&name=${encodeURIComponent(downloadItem.filename || "this file")}`
      ),
      type: "popup",
      width: 380,
      height: 220
    });
  });
});
