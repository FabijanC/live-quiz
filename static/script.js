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
    const ws_scheme = window.location.protocol.replace("http", "ws");
    let ws = new WebSocket(ws_scheme + "//" + window.location.hostname + ":8765");
    ws.onopen = (msg) => {
    };

    ws.onmessage = (msg) => {
        const data = JSON.parse(msg.data);
        if (data.type === "question") {
            console.log("new q: " + data.content);
            add_new_message(`[PITANJE] ${data.content}`);
            $("#question").html(data.content);
            $("#revealed").text("");

        } else if (data.type === "answer") {
            console.log("answer received ");
            console.log(data);
            
            const author_txt = (data.author === null) ? "Nitko ne zna" : data.author;
            const rounded = parseFloat(data.time).toFixed(2);
            const time_txt = data.time ? `(${rounded} s)` : "";
            add_new_message(`[ODGOVOR] ${author_txt}: ${data.content} ${time_txt}`);
            $("#revealed").text(data.content);
            
        } else if (data.type === "message") {
            add_new_message(`${data.author}: ${data.content}`);

        } else if (data.type === "users") {
            users = data.content;
            users.sort((u1,u2) => u2.score - u1.score);
            $("#users").html(
                `<caption>Online: ${users.length}</caption>` + users.map(
                    u => `<tr><td>${u.name}</td><td>${u.score}</td></tr>`
                ).join("")
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