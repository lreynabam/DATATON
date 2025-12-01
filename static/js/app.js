console.log("app.js cargado");

document.addEventListener("DOMContentLoaded", () => {
  const btnAnalizar = document.getElementById("btn-analizar");
  const inputArchivo = document.getElementById("archivo-json");
  const tabla = document.getElementById("tabla-resultados");
  const mensajeDiv = document.getElementById("mensaje");
  const btnDescargar = document.getElementById("btn-descargar");

  if (!btnAnalizar || !inputArchivo || !tabla || !btnDescargar) {
    console.error("No se encontraron los elementos necesarios en el DOM.");
    return;
  }

  // 🔒 No permitir descargar hasta que se haya analizado
  btnDescargar.disabled = true;

  // Ocultar tabla inicialmente (DataTables la mostrará cuando haya datos)
  tabla.style.display = "none";

  // ==============================
  // FUNCIONES SWEETALERT (Loader)
  // ==============================

  function mostrarLoader(texto = "Procesando...") {
    Swal.fire({
      title: texto,
      allowOutsideClick: false,
      allowEscapeKey: false,
      showConfirmButton: false,
      didOpen: () => {
        Swal.showLoading(); // solo usamos el loader nativo de SweetAlert2
      }
    });
  }

  function cerrarLoader() {
    Swal.close();
  }

  // ==============================
  // BOTÓN ANALIZAR
  // ==============================

  btnAnalizar.addEventListener("click", async () => {
    console.log("Click en Analizar");

    const file = inputArchivo.files[0];
    if (!file) {
      Swal.fire("Ups", "Primero selecciona un archivo JSON.", "warning");
      return;
    }

    const formData = new FormData();
    formData.append("json_file", file);

    mostrarLoader("Analizando archivo...");

    try {
      mensajeDiv.textContent = "";
      tabla.innerHTML = "";

      // Si ya hay un DataTable, destruirlo antes de crear uno nuevo
      if ($.fn.DataTable.isDataTable("#tabla-resultados")) {
        $("#tabla-resultados").DataTable().destroy();
      }

      const res = await fetch("/api/detectar-anomalias-archivo", {
        method: "POST",
        body: formData,
      });

      cerrarLoader();

      console.log("🔎 Status respuesta:", res.status);

      if (!res.ok) {
        const text = await res.text();
        console.error("Error en respuesta:", text);
        Swal.fire("Error", "Error al procesar el archivo en el servidor.", "error");
        return;
      }

      const data = await res.json();
      console.log("Respuesta JSON:", data);

      const anom = data.tramos_anomalos || [];
      mensajeDiv.textContent =
        `Se encontraron ${data.num_anomalos ?? anom.length} tramos anómalos.`;

      if (anom.length === 0) {
        tabla.style.display = "none";
        Swal.fire("Sin anomalías", "No se detectaron tramos anómalos.", "info");
        // No habilitamos descarga si no hay anomalías
        btnDescargar.disabled = true;
        return;
      }

      // const top = anom.slice(0, 20);
      const top = anom;   // sin límite
      
      let html = `
        <thead>
          <tr>
            <th>Persona</th>
            <th>Año previo</th>
            <th>Año actual</th>
            <th>Δ Patrimonio</th>
            <th>Ingresos acumulados</th>
            <th>Score</th>
          </tr>
        </thead>
        <tbody>
      `;

      for (const row of top) {
        html += `
          <tr>
            <td>${row.id_persona || ""}</td>
            <td>${row.anio_prev ?? ""}</td>
            <td>${row.anio ?? ""}</td>
            <td>${row.delta_patrimonio ?? ""}</td>
            <td>${row.ingresos_acumulados ?? ""}</td>
            <td>${row.anomalia_score ?? ""}</td>
          </tr>
        `;
      }

      html += "</tbody>";
      tabla.innerHTML = html;
      tabla.style.display = "table";

      // Inicializar DataTable
      $("#tabla-resultados").DataTable({
        pageLength: 10,
        lengthChange: true,
        lengthMenu: [     
          [10, 20, 50, 100],
          [10, 20, 50, 100]
        ],
        searching: true,
        ordering: true,
        info: true,
        select: true,
        select: {
          style: "single"
        },
        language: {
          url: "https://cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json"
        }
      });

      // ✅ Ahora sí habilitamos la descarga
      btnDescargar.disabled = false;

    } catch (err) {
      cerrarLoader();
      console.error("Error en fetch:", err);
      Swal.fire("Error", "Ocurrió un error de conexión con la API.", "error");
      btnDescargar.disabled = true;
    }
  });

  // ==============================
  // BOTÓN DESCARGAR
  // ==============================

  btnDescargar.addEventListener("click", async () => {
    if (btnDescargar.disabled) return; // seguridad extra

    mostrarLoader("Preparando descarga...");

    try {
      const res = await fetch("/descargar/servidores_anomalos");

      if (!res.ok) {
        cerrarLoader();
        const txt = await res.text();
        console.error("Error descarga:", txt);
        Swal.fire("Error", "No se pudo descargar. ¿Ya ejecutaste el análisis?", "error");
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = "servidores_anomalos.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      cerrarLoader();
      Swal.fire("Éxito", "Archivo descargado correctamente.", "success");

    } catch (e) {
      cerrarLoader();
      console.error(e);
      Swal.fire("Error", "Error de conexión al intentar descargar el archivo.", "error");
    }
  });

});
