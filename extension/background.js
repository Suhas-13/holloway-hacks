let webSocket = null;
let running = false;

function connectWebSocket() {
    if (running) return;
    running = true;

    webSocket = new WebSocket("ws://localhost:8001");

    webSocket.onopen = function (event) {
        console.log("WebSocket open");
    };

    webSocket.onclose = function (event) {
        console.log("WebSocket closed");
        running = false;
        webSocket = null;
        setTimeout(connectWebSocket, 1000); // Reconnect after 10 seconds
    };

    webSocket.onerror = function (event) {
        console.error("WebSocket error", event);
        if (webSocket) {
            running = false;
            webSocket.close();
        }
    };

    webSocket.onmessage = function (event) {
        console.log("Data requested");
        processCurrentTab();
    };
}

function chunkString(str, length) {
    return str.match(new RegExp(".{1," + length + "}", "g"));
}

function truncateString(str, length) {
    if (str.length <= length) {
        return str;
    }

    return str.slice(0, length - 3) + "...";
}

function sendChunkedText(text) {
    const chunks = chunkString(text, 500);
    if (chunks) {
        chunks.forEach(function (chunk) {
            webSocket.send(chunk);
        });
    }
    webSocket.send("text:end");
}

function processCurrentTab() {
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
        if (tabs.length === 0) {
            return;
        }

        const tab = tabs[0];
        if (!tab.url || tab.url.startsWith("chrome://")) {
            webSocket.send("");
            return;
        }

        chrome.tabs.executeScript(
            tab.id,
            { code: "document.body.innerText || document.body.textContent" },
            function (results) {
                console.log("RESULTS ARE ", results);
                if (
                    chrome.runtime.lastError ||
                    !results ||
                    results.length === 0 ||
                    !results[0]
                ) {
                    console.error(
                        "Error or no content:",
                        chrome.runtime.lastError,
                    );
                    webSocket.send("pdf:" + truncateString(tab.title, 100) + ":" + tab.url);
                } else {
                    const maxTextLength = 5000; // Set maximum text length
                    const text = results[0].slice(0, maxTextLength); // Truncate text to 5000 characters
                    webSocket.send("text:start:" + truncateString(tab.title, 100) + ":" + tab.url);
                    sendChunkedText(text);
                }
            },
        );
    });
}

connectWebSocket();

// Reconnection logic with an interval
(function checkConnection() {
    if (!running) {
        connectWebSocket();
    }
    setTimeout(checkConnection, 1000); // Check connection every 1 seconds
})();
