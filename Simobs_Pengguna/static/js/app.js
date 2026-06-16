function togglePassword(id){
    let x = document.getElementById(id);
    x.type = x.type === "password" ? "text" : "password";
}

// toast
function showToast(msg){
    const t = document.getElementById("toast");
    t.innerText = msg;
    t.classList.add("show");
    setTimeout(()=>t.classList.remove("show"),2000);
}