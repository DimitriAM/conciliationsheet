let defaultCuentaNombre = '';
let ultimoResultado = null;

document.addEventListener('DOMContentLoaded', async () => {
    await cargarCuentaDefault();

    const btnConciliar = document.getElementById('btnConciliar');
    const btnExportar = document.getElementById('btnExportar');
    if (!btnConciliar) return;

    btnConciliar.addEventListener('click', async () => {
        const fechaDesde = document.getElementById('fechaDesde').value;
        const fechaHasta = document.getElementById('fechaHasta').value;

        if (!fechaDesde || !fechaHasta) { notify('Seleccione fechas', 'error'); return; }
        if (!defaultCuentaId) { notify('No hay cuenta disponible', 'error'); return; }

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
                    metodo: "desde_contabilidad",
                    vision: "empresa",
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

    grid.innerHTML = '';

    // Tabla de desarrollo: paso a paso desde saldo contable hasta saldo banco
    let dt = '';
    if (data.desarrollo && data.desarrollo.length) {
        dt += '<div class="card"><h2>Desarrollo de la Conciliación</h2><table class="desarrollo-table"><thead><tr>'
            + '<th>Fecha</th><th>Descripción</th><th>Monto</th><th>Efecto</th><th>Saldo Parcial</th>'
            + '</tr></thead><tbody>';
        for (const r of data.desarrollo) {
            const cls = r.descripcion === 'SALDO CONTABLE' || r.descripcion === 'SALDO CALCULADO' || r.descripcion === 'SALDO BANCO (segun extracto)' ? ' class="destacado"' : '';
            dt += '<tr' + cls + '>'
                + '<td>' + (r.fecha || '') + '</td>'
                + '<td>' + (r.descripcion || '') + '</td>'
                + '<td class="valor">' + (r.monto === '-' ? '-' : '$' + r.monto.toFixed(2)) + '</td>'
                + '<td>' + (r.efecto || '') + '</td>'
                + '<td class="valor">$' + (r.saldo_parcial || 0).toFixed(2) + '</td>'
                + '</tr>';
        }
        dt += '</tbody></table></div>';
    }

    // Tabla detallada: clasificación transitoria/permanente de cada partida
    if (data.partidas_conciliatorias && data.partidas_conciliatorias.length) {
        dt += '<div class="card"><h2>Partidas Conciliatorias</h2><table class="partidas-table"><thead><tr>'
            + '<th>Clasificación</th><th>Fecha</th><th>Descripción</th><th>Monto</th><th>Signo</th>'
            + '</tr></thead><tbody>';
        for (const p of data.partidas_conciliatorias) {
            const clsTag = p.clasificacion === 'transitoria' ? 'tag-transitoria' : 'tag-permanente';
            const clsLabel = p.clasificacion === 'transitoria' ? 'Transitoria' : 'Permanente';
            const signoLabel = p.signo > 0 ? '+' : '-';
            dt += '<tr><td><span class="tag ' + clsTag + '">' + clsLabel + '</span></td>'
                + '<td>' + (p.fecha || '').slice(0,10) + '</td>'
                + '<td>' + (p.descripcion || '') + '</td>'
                + '<td class="valor">$' + (p.monto || 0).toFixed(2) + '</td>'
                + '<td class="valor signo-' + (p.signo > 0 ? 'mas' : 'menos') + '">' + signoLabel + '</td></tr>';
        }
        dt += '</tbody></table></div>';
    }
    detalles.innerHTML = dt || '';
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
    csvRows.push('Saldo Contable,' + (d.saldo_segun_contabilidad || 0));
    csvRows.push('Saldo Ajustado,' + (d.saldo_ajustado || 0));
    csvRows.push('Saldo Banco Extracto,' + (d.saldo_segun_banco || 0));
    csvRows.push('');

    if (d.desarrollo && d.desarrollo.length) {
        csvRows.push('Desarrollo de la Conciliacion');
        csvRows.push('Fecha,Descripcion,Monto,Efecto,Saldo Parcial');
        for (const r of d.desarrollo) {
            const monto = r.monto === '-' ? '-' : r.monto;
            csvRows.push([r.fecha, '"' + (r.descripcion || '').replace(/"/g, '""') + '"', monto, r.efecto, r.saldo_parcial].join(','));
        }
        csvRows.push('');
    }

    if (d.partidas_conciliatorias && d.partidas_conciliatorias.length) {
        csvRows.push('Partidas Conciliatorias');
        csvRows.push('Fecha,Descripcion,Tipo,Origen,Monto,Signo,Afecta,Clasificacion,Estado');
        for (const p of d.partidas_conciliatorias) {
            const row = [
                (p.fecha || '').slice(0,10),
                '"' + (p.descripcion || '').replace(/"/g, '""') + '"',
                p.tipo || '',
                p.origen || '',
                p.monto || 0,
                p.signo > 0 ? '+' : '-',
                p.afecta || '',
                p.clasificacion || '',
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
