let ws = new WebSocket("ws://localhost:8080");

ws.onopen = () => {
    console.log("Opened");
};

ws.onerror = (e) => {
    console.log("Error:", e);
};

ws.onclose = (e) => {
    console.log("Closed:", e);
};

ws.onmessage = (e) => {
    console.log(e.data);
};