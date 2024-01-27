let webSocket = new WebSocket("ws://localhost:8001");

webSocket.onopen = (event) => {
    console.log("websocket open");
};

function chunkString(str, length) {
    return str.match(new RegExp("(.|[\r\n]){1," + length + "}", "g"));
}

webSocket.onmessage = (event) => {
    console.log("data requested");
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
        if (tabs.length == 0) {
            return;
        }

        let id = tabs[0].id;
        let url = tabs[0].url;
        let title = tabs[0].title;

        if (url.startsWith("chrome://")) {
            webSocket.send("");
            return;
        }

        chrome.tabs.executeScript(
            id,
            {
                code: "document.all[0].innerText",
                runAt: "document_start",
            },
            function (results) {
                if (results[0].length == 0) {
                    webSocket.send("pdf:" + url);
                } else {
                    webSocket.send("text:start:" + url);
                    chunkString(results[0], 500).forEach((chunk) => {
                        webSocket.send(chunk);
                    });
                    webSocket.send("text:end");
                }
            },
        );
    });
};

webSocket.onclose = (event) => {
    console.log("websocket closed");
    webSocket = null;
};
