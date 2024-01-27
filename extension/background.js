let webSocket = new WebSocket("ws://localhost:8001");

webSocket.onopen = (event) => {
    console.log("websocket open");
};

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
                    fetch(url)
                        .then((response) => response.text())
                        .then((data) => {
                            webSocket.send("pdf:" + title + ":" + data);
                        });
                } else {
                    webSocket.send("txt:" + results[0]);
                }
            },
        );
    });
};

webSocket.onclose = (event) => {
    console.log("websocket closed");
    webSocket = null;
};
