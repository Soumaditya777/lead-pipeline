document.getElementById("enrich-btn").addEventListener("click", async () => {
  let statusDiv = document.getElementById("status");
  statusDiv.innerText = "Extracting webpage metrics...";

  let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  chrome.tabs.sendMessage(tab.id, { action: "extractDOM" }, async (response) => {
    if (!response) {
      statusDiv.innerText = "Error: Could not extract page structure.";
      return;
    }
    
    statusDiv.innerText = "Sending to enrichment pipe...";
    
    try {
      // UPDATED: Changed from http://localhost:8000 to your live Railway domain
      let res = await fetch("https://web-production-2054f.up.railway.app/api/enrich-single", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(response)
      });
      let result = await res.json();
      statusDiv.innerText = "🎯 Complete! Score queued on Dashboard.";
    } catch (err) {
      statusDiv.innerText = "Failed connection to live Railway backend app.";
    }
  });
});