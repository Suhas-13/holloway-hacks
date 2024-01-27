let webSocket = new WebSocket("ws://localhost:8001");

webSocket.onopen = (event) => {
    console.log("websocket open");
    webSocket.send("Hello from the client!");

    // chrome.tabs.onUpdated.addListener(function (tabId, changeInfo, tab) {
    //     console.log("yoo");
    //     console.log(tab);
    //     // tab.executeScript(
    //     //     null,
    //     //     {
    //     //         code: "document.all[0].innerText",
    //     //         runAt: "document_start",
    //     //     },
    //     //     function (results) {
    //     //         webSocket.send(results[0]);
    //     //     },
    //     // );
    // });
};

webSocket.onmessage = (event) => {
    console.log(`websocket received message: ${event.data}`);

    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
        if (tabs.length == 0) {
            return;
        }

        let id = tabs[0].id;

        chrome.tabs.executeScript(
            id,
            {
                code: "document.all[0].innerText",
                runAt: "document_start",
            },
            function (results) {
                console.log(results);
                webSocket.send(results[0]);
            },
        );
    });
};

webSocket.onclose = (event) => {
    console.log("websocket connection closed");
    webSocket = null;
};
