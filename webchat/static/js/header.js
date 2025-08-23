window.renderHeader = async function renderHeader() {
  const nav = document.getElementById("navLinks");
  if (!nav) return;
  const res = await fetch("/auth/me", { credentials: "same-origin" });
  const me = await res.json();
  nav.innerHTML = me.authenticated
    ? `Logged in as <b>${me.username}</b> | <a href="#" id="logoutLink">Logout</a>`
    : `Anonymous | <a href="/login">Login</a> | <a href="/register">Register</a>`;
  const logout = document.getElementById("logoutLink");
  if (logout) logout.addEventListener("click", async (e) => {
    e.preventDefault();
    await fetch("/auth/logout", { method: "POST", credentials: "same-origin" });
    location.reload();
  });
};
