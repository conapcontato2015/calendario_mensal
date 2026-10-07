/* Calendário de Tarefas — comportamento leve, sem bibliotecas externas. */
(function () {
  "use strict";

  /* ---------------------------------------------------------- avisos */
  document.querySelectorAll(".toast").forEach(function (t) {
    var tempo = parseInt(t.dataset.tempo || "4000", 10);
    var timer = setTimeout(function () { t.remove(); }, tempo);
    t.addEventListener("mouseenter", function () { clearTimeout(timer); });
    var x = t.querySelector(".x");
    if (x) x.addEventListener("click", function () { t.remove(); });
  });

  /* ---------------------------------------------------------- calendário */
  var imprimir = document.querySelector("[data-imprimir]");
  if (imprimir) imprimir.addEventListener("click", function () { window.print(); });

  var fechar = document.querySelector("[data-fechar-painel]");
  if (fechar) {
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") window.location.href = fechar.getAttribute("href");
    });
    var ed = document.querySelector(".prow form.edit input");
    if (ed) { ed.focus(); ed.select(); }
  }

  /* ---------------------------------------------------------- importar */
  var form = document.getElementById("form-importar");
  if (!form) return;
  var area = document.getElementById("texto");
  var previa = document.getElementById("previa");
  var url = form.dataset.previa;
  var espera = null, pedido = 0;

  function atualizar() {
    var meu = ++pedido;
    var foco = document.activeElement && previa.contains(document.activeElement) ? document.activeElement.id : null;
    var dados = new FormData(form);
    fetch(url, { method: "POST", body: dados })
      .then(function (r) { return r.text(); })
      .then(function (html) {
        if (meu !== pedido) return;          // chegou uma resposta mais nova
        previa.innerHTML = html;
        if (foco) {
          var el = document.getElementById(foco);
          if (el) { el.focus(); if (el.setSelectionRange && el.type === "text") el.setSelectionRange(el.value.length, el.value.length); }
        }
      })
      .catch(function () {
        previa.innerHTML = '<div class="box bad"><h3>Sem resposta do servidor</h3><p>Confira se a janela do sistema ainda está aberta no computador.</p></div>';
      });
  }

  function agendar(ms) { clearTimeout(espera); espera = setTimeout(atualizar, ms); }

  area.addEventListener("input", function () { agendar(350); });
  area.addEventListener("paste", function () { agendar(50); });

  // campos dentro da prévia (nomes novos, ignorar, substituir, ver originais)
  previa.addEventListener("change", function (e) {
    if (e.target.matches("input")) agendar(0);
  });
  previa.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && e.target.matches("input[type=text]")) { e.preventDefault(); agendar(0); }
  });
  previa.addEventListener("click", function (e) {
    var b = e.target.closest("[data-sugerir]");
    if (!b) return;
    var alvo = document.getElementById(b.dataset.sugerir);
    if (alvo) { alvo.value = b.dataset.valor; agendar(0); }
  });

  // não deixa enviar com Enter dentro dos campos de nome
  form.addEventListener("submit", function (e) {
    var btn = form.querySelector("button[type=submit]");
    if (btn && btn.disabled) e.preventDefault();
  });
})();
