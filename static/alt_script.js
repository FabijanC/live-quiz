if (!("WebSocket" in window || "MozWebSocket" in window)) {
    document.getElementById("question").innerHTML = "WebSocket protocol not supported. Please upgrade to a modern browser.";
    // document.write("<h3>WebSocket protocol not supported. Please upgrade to a modern browser.</h3>")
    // window.stop();
}