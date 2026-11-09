(function () {
  "use strict";

  // Menu lateral no celular
  var botao = document.getElementById("menu-toggle");
  var menu = document.getElementById("sidebar");
  if (botao && menu) {
    botao.addEventListener("click", function () {
      var aberto = menu.classList.toggle("aberta");
      botao.setAttribute("aria-expanded", aberto ? "true" : "false");
    });
  }

  // Confirmacao antes de enviar formularios com data-confirmar
  document.addEventListener("submit", function (e) {
    var msg = e.target.getAttribute("data-confirmar");
    if (msg && !window.confirm(msg)) e.preventDefault();
  });

  // Mascaras (apenas visuais: o servidor guarda somente os digitos)
  function digitos(v) { return v.replace(/\D/g, ""); }

  var mascaras = {
    cep: function (v) {
      v = digitos(v).slice(0, 8);
      return v.length > 5 ? v.slice(0, 5) + "-" + v.slice(5) : v;
    },
    telefone: function (v) {
      v = digitos(v).slice(0, 11);
      if (v.length > 10) return "(" + v.slice(0, 2) + ") " + v.slice(2, 7) + "-" + v.slice(7);
      if (v.length > 6) return "(" + v.slice(0, 2) + ") " + v.slice(2, 6) + "-" + v.slice(6);
      if (v.length > 2) return "(" + v.slice(0, 2) + ") " + v.slice(2);
      return v;
    },
    documento: function (v) {
      var tipo = document.getElementById("tipo_pessoa");
      var pj = tipo && tipo.value === "PJ";
      v = digitos(v).slice(0, pj ? 14 : 11);
      if (pj) {
        return v.replace(/^(\d{2})(\d)/, "$1.$2").replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
                .replace(/\.(\d{3})(\d)/, ".$1/$2").replace(/(\d{4})(\d)/, "$1-$2");
      }
      return v.replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
              .replace(/(\d{3})\.(\d{3})\.(\d{3})(\d)/, "$1.$2.$3-$4");
    }
  };

  function aplicar(campo) {
    var fn = mascaras[campo.getAttribute("data-mascara")];
    if (fn) campo.value = fn(campo.value);
  }

  document.querySelectorAll("[data-mascara]").forEach(function (campo) {
    campo.addEventListener("input", function () { aplicar(campo); });
  });

  var tipo = document.getElementById("tipo_pessoa");
  if (tipo) {
    tipo.addEventListener("change", function () {
      var doc = document.getElementById("documento");
      if (doc) aplicar(doc);
    });
  }
})();
