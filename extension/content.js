// Scrapes context information out of visible page content
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "extractDOM") {
    let pageTitle = document.title;
    let url = window.location.hostname;
    
    // Naive structural fallbacks for LinkedIn profiles vs standard websites
    let parsedName = document.querySelector("h1") ? document.querySelector("h1").innerText.trim() : "Target Entity";
    
    sendResponse({
      name: parsedName,
      company: pageTitle.split("|")[0].trim(),
      domain: url,
      title: "Prospect Contact Node"
    });
  }
  return true;
});