let defaultCuentaNombre = '';
let ultimoResultado = null;

function leerSaldosLocal() {
    try {
        const raw = localStorage.getItem('saldos_default');
        if (raw) return JSON.parse(raw);
    } catch (e) {}
    return {};
}

document.addEventListener('DOMContentLoaded', async () => {
    await cargarCuentaDefault();

    const btnConciliar = document.getElementById('btnConciliar');
    const btnExportar = document.getElementById('btnExportar');
    if (!btnConciliar) return;

    btnConciliar.addEventListener('click', async () => {
        const fechaDesde = document.getElementById('fechaDesde').value;
        const fechaHasta = document.getElementById('fechaHasta').value;
        const metodo = document.getElementById('metodoSelect').value;

        if (!fechaDesde || !fechaHasta) { notify('Seleccione fechas', 'error'); return; }
        if (!defaultCuentaId) { notify('No hay cuenta disponible', 'error'); return; }

        const saldos = leerSaldosLocal();

        btnConciliar.disabled = true;
        btnConciliar.innerHTML = '<span class="spinner"></span> Conciliando...';

        try {
            const res = await fetch(API + '/conciliate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    cuenta_id: defaultCuentaId,
                    fecha_desde: fechaDesde,
                    fecha_hasta: fechaHasta,
                    metodo,
                    vision: "empresa",
                    saldo_final_banco: saldos.saldo_final_banco,
                    saldo_final_contable: saldos.saldo_final_contable,
                    saldo_inicial_banco: saldos.saldo_inicial_banco,
                    saldo_inicial_contable: saldos.saldo_inicial_contable,
                }),
            });
            const data = await res.json();

            if (res.ok) {
                ultimoResultado = data;
                mostrarResultados(data);
                notify('Conciliacion ' + (data.conciliado ? 'exitosa' : 'completada con diferencias'), data.conciliado ? 'success' : 'warning');
                if (btnExportar) btnExportar.style.display = '';
            } else {
                notify(data.error || 'Error desconocido', 'error');
            }
        } catch (err) {
            notify('Error de conexion con el servidor', 'error');
        } finally {
            btnConciliar.disabled = false;
            btnConciliar.textContent = 'Conciliar';
        }
    });

    btnExportar?.addEventListener('click', exportarConciliacion);
});

async function cargarCuentaDefault() {
    try {
        const res = await fetch(API + '/cuenta/default');
        const data = await res.json();
        defaultCuentaId = data.id;
        defaultCuentaNombre = data.nombre || 'Cuenta Principal';
        const info = document.getElementById('cuentaInfo');
        if (info) {
            info.textContent = defaultCuentaNombre;
            info.style.display = '';
        }
    } catch (e) {
        console.error('Error al cargar cuenta default:', e);
    }
}

function mostrarResultados(data) {
    const grid = document.getElementById('resultadosGrid');
    const detalles = document.getElementById('detallesConciliacion');

    let html = '';
    html += '<div class="stat-card ' + (data.conciliado ? 'green' : 'red') + '"><div class="value">' + (data.conciliado ? '✓ Conciliado' : '✗ Diferencia') + '</div><div class="label">$' + (data.diferencia || 0).toFixed(2) + '</div></div>';

    if (data.metodo === 'cuadrada') {
        // Forma 1: Contabilidad → Banco
        const f1 = data.forma_1 || {};
        const f2 = data.forma_2 || {};
        const sf = data.saldos_finales || {};
        html += '<div class="stat-card blue"><div class="value">$' + (f1.saldo_segun_contabilidad || 0).toFixed(2) + '</div><div class="label">Saldo Contable (inicio Forma 1)</div></div>';
        html += '<div class="stat-card blue"><div class="value">$' + (f2.saldo_segun_banco || 0).toFixed(2) + '</div><div class="label">Saldo Banco (inicio Forma 2)</div></div>';
        if (f1.saldo_banco_calculado != null) {
            html += '<div class="stat-card green"><div class="value">$' + (f1.saldo_banco_calculado || 0).toFixed(2) + '</div><div class="label">Banco Calculado (Forma 1)</div></div>';
        }
        if (f2.saldo_contable_calculado != null) {
            html += '<div class="stat-card green"><div class="value">$' + (f2.saldo_contable_calculado || 0).toFixed(2) + '</div><div class="label">Contab Calculado (Forma 2)</div></div>';
        }
        if (sf.saldo_banco_final != null) {
            html += '<div class="stat-card blue"><div class="value">$' + (sf.saldo_banco_final || 0).toFixed(2) + '</div><div class="label">Saldo Banco Extracto</div></div>';
        }
        if (sf.saldo_contable_final != null) {
            html += '<div class="stat-card blue"><div class="value">$' + (sf.saldo_contable_final || 0).toFixed(2) + '</div><div class="label">Saldo Contable Libros</div></div>';
        }
    } else if (data.metodo === 'forma_1') {
        // Forma 1: Contabilidad → Banco
        html += '<div class="stat-card blue"><div class="value">$' + (data.saldo_segun_contabilidad || 0).toFixed(2) + '</div><div class="label">Saldo Contable (partida)</div></div>';
        const aj = data.detalle_ajustes || {};
        if (Object.keys(aj).length) {
            let totalAjustes = 0;
            let ajustesStr = '';
            for (const [k, v] of Object.entries(aj)) {
                if (v !== 0) {
                    ajustesStr += '<div style="font-size:0.8rem;color:#555;">' + k.replace(/_/g,' ') + ': ' + (v > 0 ? '+' : '') + '$' + v.toFixed(2) + '</div>';
                    totalAjustes += v;
                }
            }
            html += '<div class="stat-card orange"><div class="label">Ajustes</div>' + ajustesStr + '</div>';
        }
        if (data.saldo_banco_calculado != null) {
            html += '<div class="stat-card green"><div class="value">$' + (data.saldo_banco_calculado || 0).toFixed(2) + '</div><div class="label">Banco Calculado (Forma 1)</div></div>';
        }
        html += '<div class="stat-card blue"><div class="value">$' + (data.saldo_segun_banco || 0).toFixed(2) + '</div><div class="label">Saldo Banco Extracto</div></div>';
    } else if (data.metodo === 'forma_2') {
        // Forma 2: Banco → Contabilidad
        html += '<div class="stat-card blue"><div class="value">$' + (data.saldo_segun_banco || 0).toFixed(2) + '</div><div class="label">Saldo Banco Extracto (partida)</div></div>';
        const aj = data.detalle_ajustes || {};
        if (Object.keys(aj).length) {
            let ajustesStr = '';
            for (const [k, v] of Object.entries(aj)) {
                if (v !== 0) {
                    ajustesStr += '<div style="font-size:0.8rem;color:#555;">' + k.replace(/_/g,' ') + ': ' + (v > 0 ? '+' : '') + '$' + v.toFixed(2) + '</div>';
                }
            }
            html += '<div class="stat-card orange"><div class="label">Ajustes</div>' + ajustesStr + '</div>';
        }
        if (data.saldo_contable_calculado != null) {
            html += '<div class="stat-card green"><div class="value">$' + (data.saldo_contable_calculado || 0).toFixed(2) + '</div><div class="label">Contab Calculado (Forma 2)</div></div>';
        }
        html += '<div class="stat-card blue"><div class="value">$' + (data.saldo_segun_contabilidad || 0).toFixed(2) + '</div><div class="label">Saldo Contable Libros</div></div>';
    } else {
        // Fallback generico
        html += '<div class="stat-card blue"><div class="value">$' + (data.saldo_segun_banco || 0).toFixed(2) + '</div><div class="label">Saldo Según Banco</div></div>';
        html += '<div class="stat-card blue"><div class="value">$' + (data.saldo_segun_contabilidad || 0).toFixed(2) + '</div><div class="label">Saldo Según Contabilidad</div></div>';
    }
    grid.innerHTML = html;

    if (data.partidas_conciliatorias && data.partidas_conciliatorias.length) {
        let dt = '<div class="card"><h2>Partidas Conciliatorias</h2><table><thead><tr><th>Fecha</th><th>Descripción</th><th>Tipo</th><th>Origen</th><th>Debe</th><th>Haber</th></tr></thead><tbody>';
        for (const p of data.partidas_conciliatorias) {
            dt += '<tr><td>' + (p.fecha || '').slice(0,10) + '</td><td>' + (p.descripcion || '') + '</td><td><span class="tag tag-' + (p.tipo || '') + '">' + (p.tipo || '-') + '</span></td><td>' + (p.origen || '-') + '</td><td>$' + (p.debe || 0).toFixed(2) + '</td><td>$' + (p.haber || 0).toFixed(2) + '</td></tr>';
        }
        dt += '</tbody></table></div>';
        detalles.innerHTML = dt;
    } else {
        detalles.innerHTML = '';
    }
}

function exportarConciliacion() {
    if (!ultimoResultado) {
        notify('No hay datos para exportar', 'warning');
        return;
    }

    const d = ultimoResultado;
    const id = d.conciliacion_id || 'conciliacion';

    let csvRows = [];
    csvRows.push('Resumen Conciliacion');
    csvRows.push('Conciliacion ID,' + (id));
    csvRows.push('Metodo,' + (d.metodo || ''));
    csvRows.push('Conciliado,' + (d.conciliado ? 'Si' : 'No'));
    csvRows.push('Diferencia,' + (d.diferencia || 0));

    if (d.metodo === 'cuadrada') {
        const f1 = d.forma_1 || {};
        const f2 = d.forma_2 || {};
        const sf = d.saldos_finales || {};
        csvRows.push('');
        csvRows.push('--- FORMA 1: Contabilidad → Banco ---');
        csvRows.push('Saldo Contable (inicio),' + (f1.saldo_segun_contabilidad || 0));
        const aj1 = f1.ajustes || {};
        for (const [k, v] of Object.entries(aj1)) {
            csvRows.push('Ajuste ' + k + ',' + (v > 0 ? '+' : '') + v.toFixed(2));
        }
        csvRows.push('Banco Calculado,' + (f1.saldo_banco_calculado || 0));
        csvRows.push('Saldo Banco Extracto,' + (sf.saldo_banco_final || 0));
        csvRows.push('Diferencia Forma 1,' + (f1.diferencia || 0));
        csvRows.push('');
        csvRows.push('--- FORMA 2: Banco → Contabilidad ---');
        csvRows.push('Saldo Banco (inicio),' + (f2.saldo_segun_banco || 0));
        const aj2 = f2.ajustes || {};
        for (const [k, v] of Object.entries(aj2)) {
            csvRows.push('Ajuste ' + k + ',' + (v > 0 ? '+' : '') + v.toFixed(2));
        }
        csvRows.push('Contab Calculado,' + (f2.saldo_contable_calculado || 0));
        csvRows.push('Saldo Contable Libros,' + (sf.saldo_contable_final || 0));
        csvRows.push('Diferencia Forma 2,' + (f2.diferencia || 0));
    } else if (d.metodo === 'forma_1') {
        csvRows.push('');
        csvRows.push('--- FORMA 1: Contabilidad → Banco ---');
        csvRows.push('Saldo Contable (partida),' + (d.saldo_segun_contabilidad || 0));
        const aj = d.detalle_ajustes || {};
        for (const [k, v] of Object.entries(aj)) {
            csvRows.push('Ajuste ' + k + ',' + (v > 0 ? '+' : '') + v.toFixed(2));
        }
        csvRows.push('Banco Calculado,' + (d.saldo_banco_calculado || 0));
        csvRows.push('Saldo Banco Extracto,' + (d.saldo_segun_banco || 0));
    } else if (d.metodo === 'forma_2') {
        csvRows.push('');
        csvRows.push('--- FORMA 2: Banco → Contabilidad ---');
        csvRows.push('Saldo Banco (partida),' + (d.saldo_segun_banco || 0));
        const aj = d.detalle_ajustes || {};
        for (const [k, v] of Object.entries(aj)) {
            csvRows.push('Ajuste ' + k + ',' + (v > 0 ? '+' : '') + v.toFixed(2));
        }
        csvRows.push('Contab Calculado,' + (d.saldo_contable_calculado || 0));
        csvRows.push('Saldo Contable Libros,' + (d.saldo_segun_contabilidad || 0));
    } else {
        csvRows.push('');
        csvRows.push('Saldo Segun Banco,' + (d.saldo_segun_banco || 0));
        csvRows.push('Saldo Segun Contabilidad,' + (d.saldo_segun_contabilidad || 0));
        csvRows.push('Saldo Banco Ajustado,' + (d.saldo_banco_ajustado || 0));
        csvRows.push('Saldo Contable Ajustado,' + (d.saldo_contable_ajustado || 0));
    }

    csvRows.push('');

    if (d.partidas_conciliatorias && d.partidas_conciliatorias.length) {
        csvRows.push('Partidas Conciliatorias');
        csvRows.push('Fecha,Descripcion,Tipo,Origen,Debe,Haber,Estado');
        for (const p of d.partidas_conciliatorias) {
            const row = [
                (p.fecha || '').slice(0,10),
                '"' + (p.descripcion || '').replace(/"/g, '""') + '"',
                p.tipo || '',
                p.origen || '',
                p.debe || 0,
                p.haber || 0,
                p.estado || '',
            ];
            csvRows.push(row.join(','));
        }
    }

    const csv = csvRows.join('\r\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'conciliacion_' + id + '.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    notify('Exportado como CSV', 'success');
}
