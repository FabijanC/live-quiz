if (window.location.protocol == "https:") {
    var ws_scheme = "wss://";
} else {
    var ws_scheme = "ws://"
}

const MAX_MESSAGES = 10;
var messages = [];
var my_name = "";

function add_new_message(msg) {
    messages.push(msg);
    if (messages.lenth > MAX_MESSAGES) {
        messages.shift();
    }

    if (messages.length > MAX_MESSAGES) {
        messages.shift();
    }
    $("#messages").html(
        messages.map(m => `<tr><td>${m}</td></tr>`).join("")
    );
}

if (!("WebSocket" in window || "MozWebSocket" in window)) {
    document.write("WebSocket protocol not supported. Please upgrade to a modern browser.")
    window.stop();
} else {
    let ws = new WebSocket(ws_scheme + "localhost:8765");
    ws.onopen = (msg) => {
    };

    ws.onmessage = (msg) => {
        data = JSON.parse(msg.data);
        if (data.type === "question") {
            console.log("new q: " + data.content);
            $("#question").html(data.content);
            $("#revealed").text("");

        } else if (data.type === "answer") {
            console.log("answer received");
            add_new_message(data.content);
            $("#revealed").text(data.content);
            
        } else if (data.type === "message") {
            add_new_message(data.content);

        } else if (data.type === "users") {
            users = data.content;
            $("#users").html(
                `<caption>Players: ${users.length}</caption>` + users.map(u => `<tr><td>${u}</td></tr>`).join("")
            );

            let my_name_cell = $("#users td").filter(function() {
                const txt = $(this).text().trim();
                return txt === my_name;
            });
            my_name_cell.css("font-weight", "bold");
        } else if (data.type === "my_name") {
            my_name = data.content;
        }
    };

    $("#answer").on("keyup", (e) => {
        if (String.fromCharCode(e.keyCode) === "\r") {
            const msg = $("#answer").val().trim();
            if (msg !== "") {
                ws.send(msg);
                $("#answer").val("");
            }
        }
    });
}