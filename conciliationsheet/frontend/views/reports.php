<div class="flex-between mb-2">
    <h2>Reportes</h2>
    <div class="flex gap-1">
        <button class="btn btn-secondary" id="btnRefreshReportes">Actualizar</button>
        <button class="btn btn-primary" id="btnExportExcel">Exportar Excel</button>
        <button class="btn btn-primary" id="btnExportPDF">Exportar PDF</button>
    </div>
</div>

<div class="card">
    <h2>Filtros</h2>
    <div class="filters">
        <select id="reportCuentaSelect">
            <option value="">Todas las cuentas</option>
        </select>
        <select id="reportFilterTipo">
            <option value="">Todos los tipos</option>
            <option value="permanente">Permanente</option>
            <option value="transitoria">Transitoria</option>
        </select>
        <select id="reportFilterEstado">
            <option value="">Todos los estados</option>
            <option value="pendiente">Pendiente</option>
            <option value="ajustada">Ajustada</option>
            <option value="resuelta">Resuelta</option>
        </select>
        <input type="date" id="reportFechaDesde" placeholder="Fecha desde">
        <input type="date" id="reportFechaHasta" placeholder="Fecha hasta">
    </div>
</div>

<div class="stats-grid" id="reportStats"></div>

<div class="card">
    <h2>Resumen por Tipo</h2>
    <div id="resumenTabla" style="overflow-x:auto;"><p style="color:#888;">Sin datos disponibles.</p></div>
</div>

<div class="card">
    <h2>Últimas Partidas Conciliatorias</h2>
    <div id="ultimasPartidas" style="overflow-x:auto;"><p style="color:#888;">Sin datos disponibles.</p></div>
</div>

<script>
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('reportStats')) {
        cargarCuentasReportes();
    }
});
</script>
