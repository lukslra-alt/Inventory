/**
 * Monitors and updates the visual interface state 
 * based on the user's live device internet connection.
 */
function updateNetworkStatus() {
    const status = document.getElementById("network-status");
    
    // Safety escape exit if element isn't rendered on the active view
    if (!status) {
        return;
    }

    if (navigator.onLine) {
        // Switch contextual color variants while keeping layout classes intact
        status.classList.remove("alert-warning");
        status.classList.add("alert-success");
        status.innerHTML = "🟢 Online - Live Data";
    } else {
        // Shift styles seamlessly when connection drops
        status.classList.remove("alert-success");
        status.classList.add("alert-warning");
        status.innerHTML = "🔴 Offline - Cached Data";
    }
}

// Bind live connection toggles across browser interface runtimes
window.addEventListener("online", updateNetworkStatus);
window.addEventListener("offline", updateNetworkStatus);

// Guarantee script calculation fires completely during initial document loading phases
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", updateNetworkStatus);
} else {
    updateNetworkStatus();
}
