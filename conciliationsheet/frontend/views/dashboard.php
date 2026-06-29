<div class="flex-between mb-2">
    <h2>Conciliación</h2>
    <div class="flex gap-1" style="flex-wrap:wrap;">
        <span id="cuentaInfo" style="background:#e3f2fd;color:#1565c0;padding:0.4rem 1rem;border-radius:8px;font-size:0.9rem;font-weight:600;display:none;"></span>
        <input type="date" id="fechaDesde">
        <input type="date" id="fechaHasta">
        <select id="metodoSelect">
            <option value="1">Forma 1: Contabilidad → Banco</option>
            <option value="2">Forma 2: Banco → Contabilidad</option>
            <option value="cuadrada">Forma 3: Cuadrada (ambas)</option>
        </select>
        <button class="btn btn-primary" id="btnConciliar">Conciliar</button>
        <button class="btn btn-secondary" id="btnExportar" style="display:none;">Exportar</button>
    </div>
</div>

<div class="stats-grid" id="resultadosGrid">
    <div class="stat-card blue"><div class="value">-</div><div class="label">Seleccione fechas y concilie</div></div>
</div>

<div id="detallesConciliacion"></div>

<script>
document.addEventListener('DOMContentLoaded', () => {
    const hoy = new Date();
    const mes = hoy.getMonth();
    const anio = hoy.getFullYear();
    document.getElementById('fechaDesde').value = new Date(anio, mes, 1).toISOString().slice(0,10);
    document.getElementById('fechaHasta').value = hoy.toISOString().slice(0,10);
});
</script>
