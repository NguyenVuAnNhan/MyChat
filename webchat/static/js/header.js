function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
  }
  
  function renderHeader() {
    const username = getCookie("username");
    console.log(username)
    const nav = document.getElementById("navLinks");
    nav.innerHTML = "";
  
    if (username) {
      nav.innerHTML = `
        Logged in as <b>${username}</b>
        <a href="#" id="logoutLink">Logout</a>
      `;
      document.getElementById("logoutLink").addEventListener("click", async (e) => {
        e.preventDefault();
        await fetch("/api/logout", { method: "POST" });
        document.cookie = "username=; Max-Age=0; path=/";
        location.reload();
      });
    } else {
      nav.innerHTML = `
        Anonymous |
        <a href="/login">Login</a> |
        <a href="/register">Register</a>
      `;
    }
  }
  
  document.addEventListener("DOMContentLoaded", renderHeader);
  