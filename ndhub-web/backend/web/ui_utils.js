(function initNdHubUiUtils(globalScope) {
  function escapeHtml(text) {
    const value = String(text ?? "");
    return value
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function wrapResponsiveTables() {
    const tables = Array.from(document.querySelectorAll("table"));
    for (const table of tables) {
      const parent = table.parentElement;
      if (!parent || parent.classList.contains("table-shell")) continue;
      const shell = document.createElement("div");
      shell.className = "table-shell table-scroll";
      parent.insertBefore(shell, table);
      shell.appendChild(table);
    }
  }

  function appendCell(tr, text) {
    const td = document.createElement("td");
    td.textContent = String(text ?? "");
    tr.appendChild(td);
    return td;
  }

  function appendHtmlCell(tr, html) {
    const td = document.createElement("td");
    td.innerHTML = String(html || "");
    tr.appendChild(td);
    return td;
  }

  globalScope.NDHubUIUtils = {
    escapeHtml,
    wrapResponsiveTables,
    appendCell,
    appendHtmlCell,
  };
})(window);

