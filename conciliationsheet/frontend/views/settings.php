<div class="flex-between mb-2">
    <h2>Historial de Conciliaciones</h2>
    <button class="btn btn-secondary" id="btnRefreshHistorial" style="font-size:0.85rem;">Actualizar</button>
</div>

<div class="card">
    <div id="historialContainer">
        <p style="color:#888;">Seleccione una cuenta para ver el historial...</p>
    </div>
</div>

<script>
let _settingsCuentaId = null;

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch(API + '/cuenta/default');
        const data = await res.json();
        _settingsCuentaId = data.id;
    } catch (e) {
        const el = document.getElementById('historialContainer');
        if (el) el.innerHTML = '<p style="color:#721c24;">Error al obtener cuenta</p>';
        return;
    }
    await cargarHistorial();
    document.getElementById('btnRefreshHistorial')?.addEventListener('click', cargarHistorial);
});

async function cargarHistorial() {
    const container = document.getElementById('historialContainer');
    if (!container || !_settingsCuentaId) return;

    container.innerHTML = '<p style="color:#888;">Cargando...</p>';

    try {
        const res = await fetch(API + '/conciliate/history?cuenta_id=' + _settingsCuentaId);
        if (!res.ok) {
            container.innerHTML = '<p style="color:#721c24;">Error al cargar historial</p>';
            return;
        }
        const data = await res.json();

        if (!data.data || data.data.length === 0) {
            container.innerHTML = '<p style="color:#888;">No hay conciliaciones registradas. Realice una conciliaci&oacute;n desde el Dashboard.</p>';
            return;
        }

        let html = '<table class="data-table"><thead><tr>';
        html += '<th>ID</th><th>Fecha Cierre</th><th>Saldo Contable</th><th>Saldo Banco</th><th>Diferencia</th><th>Estado</th><th>Conciliado</th><th>Acci&oacute;n</th>';
        html += '</tr></thead><tbody>';

        for (const c of data.data) {
            const diff = c.diferencia_total || 0;
            const conciliado = Math.abs(diff) < 0.01 ? 'CONCILIADO' : 'PENDIENTE';
            const estadoLabel = c.estado === 'conciliada' ? 'Conciliada' : (c.estado === 'pendiente_ajustes' ? 'Pendiente' : c.estado);
            const sc = (c.saldo_segun_contabilidad || 0).toLocaleString('es-AR', {minimumFractionDigits: 2});
            const sb = (c.saldo_segun_banco || 0).toLocaleString('es-AR', {minimumFractionDigits: 2});
            const sd = diff.toLocaleString('es-AR', {minimumFractionDigits: 2});
            html += '<tr>';
            html += '<td>' + (c.id || '-') + '</td>';
            html += '<td>' + (c.fecha_cierre || '-') + '</td>';
            html += '<td>$' + sc + '</td>';
            html += '<td>$' + sb + '</td>';
            html += '<td class="' + (Math.abs(diff) < 0.01 ? '' : 'text-danger') + '">$' + sd + '</td>';
            html += '<td>' + estadoLabel + '</td>';
            html += '<td><span class="tag tag-' + (conciliado === 'CONCILIADO' ? 'success' : 'warning') + '">' + conciliado + '</span></td>';
            html += '<td><button class="btn-del-conc" data-id="' + c.id + '" style="padding:0.2rem 0.6rem;border:none;border-radius:4px;background:#f8d7da;color:#721c24;cursor:pointer;">Eliminar</button></td>';
            html += '</tr>';
        }
        html += '</tbody></table>';
        container.innerHTML = html;

        document.querySelectorAll('.btn-del-conc').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = btn.dataset.id;
                if (!confirm('Eliminar conciliaci\u00f3n #' + id + '? Se eliminar\u00e1n sus partidas asociadas.')) return;
                btn.disabled = true;
                btn.textContent = '...';
                try {
                    const r = await fetch(API + '/conciliate/' + id, { method: 'DELETE' });
                    const result = await r.json();
                    if (r.ok) {
                        notify('Conciliaci\u00f3n eliminada', 'success');
                        cargarHistorial();
                    } else {
                        notify('Error: ' + (result.error || ''), 'error');
                        btn.disabled = false;
                        btn.textContent = 'Eliminar';
                    }
                } catch (e) {
                    notify('Error de conexi\u00f3n', 'error');
                    btn.disabled = false;
                    btn.textContent = 'Eliminar';
                }
            });
        });
    } catch (e) {
        container.innerHTML = '<p style="color:#721c24;">Error de conexi\u00f3n</p>';
    }
}
</script>
