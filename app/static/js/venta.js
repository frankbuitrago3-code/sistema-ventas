// Carrito de la pantalla "Nueva venta": añade/quita líneas y calcula el total en vivo.
(function () {
  const tbody = document.getElementById("lineas");
  const botonAgregar = document.getElementById("agregar");
  const totalEl = document.getElementById("total");
  if (!tbody) return;

  const plantilla = tbody.querySelector(".linea").cloneNode(true);

  const dinero = (centavos) =>
    "$" + (centavos / 100).toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: "always" });

  function recalcular() {
    let total = 0;
    tbody.querySelectorAll(".linea").forEach((fila) => {
      const opcion = fila.querySelector("select").selectedOptions[0];
      const cantidadInput = fila.querySelector("input[name=cantidad]");
      const precio = Number(opcion?.dataset.precio || 0);
      const stock = Number(opcion?.dataset.stock || 0);
      const cantidad = Math.max(Number(cantidadInput.value) || 0, 0);
      if (stock) cantidadInput.max = stock;
      cantidadInput.classList.toggle("invalido", stock > 0 && cantidad > stock);
      fila.querySelector(".precio").textContent = precio ? dinero(precio) : "—";
      fila.querySelector(".subtotal").textContent = precio ? dinero(precio * cantidad) : "—";
      total += precio * cantidad;
    });
    totalEl.textContent = dinero(total);
  }

  botonAgregar.addEventListener("click", () => {
    const nueva = plantilla.cloneNode(true);
    tbody.appendChild(nueva);
    nueva.querySelector("select").focus();
    recalcular();
  });

  tbody.addEventListener("click", (e) => {
    if (!e.target.closest(".quitar")) return;
    const filas = tbody.querySelectorAll(".linea");
    if (filas.length > 1) {
      e.target.closest(".linea").remove();
    } else {
      filas[0].querySelector("select").value = "";
      filas[0].querySelector("input[name=cantidad]").value = 1;
    }
    recalcular();
  });

  tbody.addEventListener("input", recalcular);
  tbody.addEventListener("change", recalcular);
  recalcular();
})();
