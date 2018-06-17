
let log = (t, err) => {
    let e = document.createElement('div');
    e.innerText = t;
    e.style.color = err ? '#e55' : '#7c4';
    document.getElementById('console').appendChild(e)
};

// let url = 'ws://159.65.126.202:5000/client';
let url = 'ws://0.0.0.0:5000/client';
let ws = new WebSocket(url);

ws.onopen = () => log(`Connected to ${url}`);
ws.onerror = (e) => log(`Unable connect to ${url}`, true);
ws.onclose = (e) => log('Closed');
ws.onmessage = (e) => log(`Message: ${e.data}`);