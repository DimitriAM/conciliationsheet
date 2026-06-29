let reportCuentaId = '';

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('reportStats')) {
        cargarReportes();
    }
    document.getElementById('btnRefreshReportes')?.addEventListener('click', cargarReportes);
    document.getElementById('reportFilterTipo')?.addEventListener('change', cargarReportes);
    document.getElementById('reportFilterEstado')?.addEventListener('change', cargarReportes);
    document.getElementById('reportFechaDesde')?.addEventListener('change', cargarReportes);
    document.getElementById('reportFechaHasta')?.addEventListener('change', cargarReportes);
    document.getElementById('btnExportExcel')?.addEventListener('click', () => exportarReporte('excel'));
    document.getElementById('btnExportPDF')?.addEventListener('click', () => exportarReporte('pdf'));
});

async function cargarCuentasReportes() {
    try {
        const res = await fetch(API + '/cuentas');
        const cuentas = await res.json();
        const sel = document.getElementById('reportCuentaSelect');
        if (!sel) return;
        sel.innerHTML = '<option value="">Todas las cuentas</option>';
        for (const c of cuentas) {
            sel.innerHTML += '<option value="' + c.id + '">' + c.nombre + ' (' + c.banco + ')</option>';
        }
        sel.addEventListener('change', () => {
            reportCuentaId = sel.value;
            cargarReportes();
        });
        cargarReportes();
    } catch (e) {
        console.error('Error:', e);
    }
}

async function cargarReportes() {
    const tipo = document.getElementById('reportFilterTipo')?.value || '';
    const estado = document.getElementById('reportFilterEstado')?.value || '';
    const fechaDesde = document.getElementById('reportFechaDesde')?.value || '';
    const fechaHasta = document.getElementById('reportFechaHasta')?.value || '';

    let url = API + '/reports/summary';
    const params = new URLSearchParams();
    if (reportCuentaId) params.append('cuenta_id', reportCuentaId);
    if (tipo) params.append('tipo', tipo);
    if (estado) params.append('estado', estado);
    if (fechaDesde) params.append('fecha_desde', fechaDesde);
    if (fechaHasta) params.append('fecha_hasta', fechaHasta);
    const qs = params.toString();
    if (qs) url += '?' + qs;

    try {
        const res = await fetch(url);
        const data = await res.json();

        renderReportStats(data);

        const partidasUrl = API + '/partidas?per_page=500' + (qs ? '&' + qs : '');
        const partidasRes = await fetch(partidasUrl);
        const partidasData = await partidasRes.json();
        renderResumenTabla(partidasData.resumen || []);
        renderUltimasPartidas(partidasData.data || []);
    } catch (err) {
        document.getElementById('reportStats').innerHTML = '<p style="color:#721c24;">Error al cargar reportes</p>';
    }
}

function renderReportStats(data) {
    const grid = document.getElementById('reportStats');
    const resumen = data.resumen || [];
    const total = data.total || 0;
    const montoTotal = data.monto_total || 0;

    let html = '';
    html += '<div class="stat-card blue"><div class="value">' + total + '</div><div class="label">Total Partidas</div></div>';
    html += '<div class="stat-card red"><div class="value">$' + montoTotal.toFixed(2) + '</div><div class="label">Monto Total</div></div>';

    const colores = { permanente: 'red', transitoria: 'orange' };
    for (const r of resumen) {
        const color = colores[r.tipo] || 'blue';
        html += '<div class="stat-card ' + color + '"><div class="value">' + r.cantidad + '</div><div class="label">' + r.tipo + '</div></div>';
    }
    grid.innerHTML = html;
}

function renderResumenTabla(resumen) {
    const div = document.getElementById('resumenTabla');
    if (!resumen.length) {
        div.innerHTML = '<p style="color:#888;">Sin datos disponibles.</p>';
        return;
    }
    let html = '<table><thead><tr><th>Tipo</th><th>Cantidad</th><th>Total Debe</th><th>Total Haber</th></tr></thead><tbody>';
    for (const r of resumen) {
        html += '<tr><td><span class="tag tag-' + r.tipo + '">' + r.tipo + '</span></td><td>' + r.cantidad + '</td><td>$' + (r.total_debe || 0).toFixed(2) + '</td><td>$' + (r.total_haber || 0).toFixed(2) + '</td></tr>';
    }
    html += '</tbody></table>';
    div.innerHTML = html;
}

function renderUltimasPartidas(items) {
    const div = document.getElementById('ultimasPartidas');
    if (!items.length) {
        div.innerHTML = '<p style="color:#888;">Sin datos disponibles.</p>';
        return;
    }
    const slice = items.slice(0, 10);
    let html = '<table><thead><tr><th>Fecha</th><th>Descripcion</th><th>Tipo</th><th>Debe</th><th>Haber</th><th>Estado</th></tr></thead><tbody>';
    for (const p of slice) {
        html += '<tr><td>' + (p.fecha || '').slice(0,10) + '</td><td>' + (p.descripcion || '') + '</td><td><span class="tag tag-' + p.tipo + '">' + (p.tipo || '-') + '</span></td><td>$' + (p.debe || 0).toFixed(2) + '</td><td>$' + (p.haber || 0).toFixed(2) + '</td><td><span class="badge badge-' + (p.estado || 'pendiente') + '">' + (p.estado || 'pendiente') + '</span></td></tr>';
    }
    html += '</tbody></table>';
    div.innerHTML = html;
}

function exportarReporte(formato) {
    const tipo = document.getElementById('reportFilterTipo')?.value || '';
    const estado = document.getElementById('reportFilterEstado')?.value || '';
    const fechaDesde = document.getElementById('reportFechaDesde')?.value || '';
    const fechaHasta = document.getElementById('reportFechaHasta')?.value || '';

    let url = API + '/reports/export?formato=' + formato;
    if (reportCuentaId) url += '&cuenta_id=' + reportCuentaId;
    if (tipo) url += '&tipo=' + tipo;
    if (estado) url += '&estado=' + estado;
    if (fechaDesde) url += '&fecha_desde=' + fechaDesde;
    if (fechaHasta) url += '&fecha_hasta=' + fechaHasta;

    window.open(url, '_blank');
}
