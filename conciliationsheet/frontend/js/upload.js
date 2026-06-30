let defaultCuentaId = null;

async function obtenerCuentaDefault() {
    try {
        const res = await fetch(API + '/cuenta/default');
        const data = await res.json();
        defaultCuentaId = data.id;
        return defaultCuentaId;
    } catch (e) {
        notify('Error al obtener cuenta por defecto', 'error');
        return null;
    }
}

function guardarSaldos(fuente) {
    const key = 'saldos_default';
    let data = {};
    try { const r = localStorage.getItem(key); if (r) data = JSON.parse(r); } catch (e) {}
    if (fuente === 'banco') {
        const si = document.getElementById('saldoInicialBanco').value;
        const sf = document.getElementById('saldoFinalBanco').value;
        if (si !== '') data.saldo_inicial_banco = parseFloat(si);
        if (sf !== '') data.saldo_final_banco = parseFloat(sf);
    } else {
        const si = document.getElementById('saldoInicialContable').value;
        const sf = document.getElementById('saldoFinalContable').value;
        if (si !== '') data.saldo_inicial_contable = parseFloat(si);
        if (sf !== '') data.saldo_final_contable = parseFloat(sf);
    }
    localStorage.setItem(key, JSON.stringify(data));
}

function setupDropHandler(dropZoneId, inputId, listId, btnId) {
    const dropZone = document.getElementById(dropZoneId);
    const fileInput = document.getElementById(inputId);
    const fileList = document.getElementById(listId);
    const btnUpload = document.getElementById(btnId);

    if (!dropZone || !fileInput || !fileList || !btnUpload) return;

    let selectedFile = null;

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) handleFile(fileInput.files[0]);
    });

    function handleFile(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['xlsx', 'xls', 'csv'].includes(ext)) {
            notify('Formato no permitido. Use .xlsx, .xls o .csv', 'error');
            return;
        }
        selectedFile = file;
        fileList.innerHTML = '';
        const li = document.createElement('li');
        li.innerHTML = `
            <div class="file-info">
                <span>${ext === 'csv' ? '📃' : '📊'}</span>
                <span>${file.name}</span>
                <span style="color:#888;font-size:0.85rem;">(${(file.size / 1024).toFixed(1)} KB)</span>
            </div>
            <span class="status status-pending">pendiente</span>
        `;
        fileList.appendChild(li);
        btnUpload.disabled = false;
    }

    return {
        getFile: () => selectedFile,
        clear: () => { selectedFile = null; fileList.innerHTML = ''; btnUpload.disabled = true; },
        getBtn: () => btnUpload,
    };
}

function setupUploadHandler(handler, statusId, fuente) {
    const statusEl = document.getElementById(statusId);
    const btnUpload = handler.getBtn();

    btnUpload.addEventListener('click', async () => {
        const file = handler.getFile();
        if (!file) return;

        if (!defaultCuentaId) {
            await obtenerCuentaDefault();
            if (!defaultCuentaId) {
                notify('No se pudo obtener la cuenta por defecto', 'error');
                return;
            }
        }

        btnUpload.disabled = true;
        statusEl.innerHTML = '<span class="spinner"></span> Subiendo...';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch(API + '/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (!res.ok) {
                statusEl.innerHTML = '<span style="color:#721c24;">Error: ' + (data.error || '') + '</span>';
                btnUpload.disabled = false;
                return;
            }

            statusEl.innerHTML = '<span style="color:#155724;">Subido. Procesando...</span>';
            document.querySelector('#' + handler.getBtn().id.replace('btnUpload', 'fileList') + ' .status').className = 'status status-ok';
            document.querySelector('#' + handler.getBtn().id.replace('btnUpload', 'fileList') + ' .status').textContent = 'subido';

            const archivo = data.archivo.nombre_archivo;

            const saldoFinalInput = document.getElementById(fuente === 'banco' ? 'saldoFinalBanco' : 'saldoFinalContable');
            const saldoFinal = saldoFinalInput ? (parseFloat(saldoFinalInput.value) || null) : null;

            const res2 = await fetch(API + '/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ archivo, cuenta_id: defaultCuentaId, fuente, saldo_final: saldoFinal }),
            });
            const data2 = await res2.json();

            if (res2.ok) {
                statusEl.innerHTML = '<span style="color:#155724;">Procesado: ' + data2.registros_insertados + ' registros</span>';
                notify(data2.registros_insertados + ' registros importados de ' + fuente, 'success');
                guardarSaldos(fuente);
            } else {
                statusEl.innerHTML = '<span style="color:#721c24;">Error al procesar: ' + (data2.error || '') + '</span>';
            }

            handler.clear();
            cargarArchivosLista();
        } catch (err) {
            statusEl.innerHTML = '<span style="color:#721c24;">Error de conexión</span>';
            btnUpload.disabled = false;
        }
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    await obtenerCuentaDefault();

    const bancoHandler = setupDropHandler('dropZoneBanco', 'fileInputBanco', 'fileListBanco', 'btnUploadBanco');
    const contableHandler = setupDropHandler('dropZoneContable', 'fileInputContable', 'fileListContable', 'btnUploadContable');

    if (bancoHandler) setupUploadHandler(bancoHandler, 'statusBanco', 'banco');
    if (contableHandler) setupUploadHandler(contableHandler, 'statusContable', 'contabilidad');

    initModalDiccionario();
    cargarArchivosLista();
    cargarDiccionario();

    document.getElementById('btnRefreshArchivos')?.addEventListener('click', cargarArchivosLista);
    document.getElementById('btnRefrescarDiccionario')?.addEventListener('click', cargarDiccionario);
    document.getElementById('btnNuevaEntrada')?.addEventListener('click', () => abrirModalDiccionario());
    document.getElementById('diccionarioFuente')?.addEventListener('change', cargarDiccionario);
});

async function cargarArchivosLista() {
    try {
        const res = await fetch(API + '/upload');
        if (!res.ok) return;
        const archivos = await res.json();
        const div = document.getElementById('archivosList');
        if (!div) return;
        if (!archivos.length) {
            div.innerHTML = '<p style="color:#888;">No hay archivos subidos.</p>';
            return;
        }
        let html = '<table><thead><tr><th>Archivo</th><th>Tamaño</th><th>Acción</th></tr></thead><tbody>';
        for (const a of archivos) {
            const nombre = a.nombre;
            const tamano = (a.tamano / 1024).toFixed(1) + ' KB';
            html += '<tr><td>' + nombre + '</td><td>' + tamano + '</td><td><button class="btn-del" data-name="' + nombre + '" style="padding:0.2rem 0.6rem;border:none;border-radius:4px;background:#f8d7da;color:#721c24;cursor:pointer;">Eliminar</button></td></tr>';
        }
        html += '</tbody></table>';
        div.innerHTML = html;

        document.querySelectorAll('.btn-del').forEach(btn => {
            btn.addEventListener('click', async () => {
                if (!confirm('Eliminar este archivo?')) return;
                const name = btn.dataset.name;
                const res = await fetch(API + '/upload/' + name, { method: 'DELETE' });
                if (res.ok) cargarArchivosLista();
                else notify('Error al eliminar', 'error');
            });
        });
    } catch (e) {
        console.error('Error al cargar archivos:', e);
    }
}

function escHtml(s) {
    if (!s) return '';
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(s) {
    return (s || '').replace(/"/g,'&quot;');
}

async function cargarDiccionario() {
    const fuente = document.getElementById('diccionarioFuente')?.value || 'banco';
    const div = document.getElementById('diccionarioList');
    if (!div) return;
    try {
        const res = await fetch(API + '/diccionario?fuente=' + fuente);
        if (!res.ok) { div.innerHTML = '<p style="color:#721c24;">Error al cargar</p>'; return; }
        const data = await res.json();
        if (!data.data.length) {
            div.innerHTML = '<p style="color:#888;">Sin entradas en el diccionario de ' + fuente + '.</p>';
            return;
        }
        let html = '<table><thead><tr><th>Patrón</th><th>Tipo</th><th>Origen</th><th>Acción</th></tr></thead><tbody>';
        for (const e of data.data) {
            html += '<tr>'
                + '<td><code>' + escHtml(e.patron) + '</code></td>'
                + '<td><span class="tag tag-' + (e.tipo || '') + '">' + (e.tipo || '-') + '</span></td>'
                + '<td>' + (e.autogenerado ? 'auto' : 'manual') + '</td>'
                + '<td><button class="btn-del-diccionario" data-id="' + e.id + '" data-patron="' + escAttr(e.patron) + '" style="padding:0.2rem 0.6rem;border:none;border-radius:4px;background:#f8d7da;color:#721c24;cursor:pointer;">Eliminar</button></td>'
                + '</tr>';
        }
        html += '</tbody></table>';
        div.innerHTML = html;

        document.querySelectorAll('.btn-del-diccionario').forEach(btn => {
            btn.addEventListener('click', async () => {
                if (!confirm('Eliminar el patrón "' + btn.dataset.patron + '" del diccionario?')) return;
                const res = await fetch(API + '/diccionario/' + btn.dataset.id, { method: 'DELETE' });
                if (res.ok) {
                    notify('Entrada eliminada', 'success');
                    cargarDiccionario();
                } else {
                    notify('Error al eliminar', 'error');
                }
            });
        });
    } catch (e) {
        div.innerHTML = '<p style="color:#721c24;">Error de conexión</p>';
    }
}

function initModalDiccionario() {
    document.getElementById('btnCancelarDiccionario')?.addEventListener('click', cerrarModalDiccionario);
    document.getElementById('modalDiccionario')?.addEventListener('click', (e) => {
        if (e.target === e.currentTarget) cerrarModalDiccionario();
    });
    document.getElementById('btnGuardarDiccionario')?.addEventListener('click', guardarEntradaDiccionario);
}

function abrirModalDiccionario(editData) {
    document.getElementById('diccionarioEditId').value = '';
    document.getElementById('diccionarioPatron').value = '';
    document.getElementById('modalDiccionarioTitle').textContent = 'Nueva Entrada en Diccionario';
    if (editData) {
        document.getElementById('modalDiccionarioTitle').textContent = 'Editar Entrada';
        document.getElementById('diccionarioEditId').value = editData.id;
        document.getElementById('diccionarioPatron').value = editData.patron;
        document.getElementById('diccionarioFuenteEdit').value = editData.fuente;
        document.getElementById('diccionarioTipo').value = editData.tipo;
    } else {
        document.getElementById('diccionarioFuenteEdit').value = document.getElementById('diccionarioFuente')?.value || 'banco';
    }
    document.getElementById('modalDiccionario')?.classList.remove('hidden');
}

function cerrarModalDiccionario() {
    document.getElementById('modalDiccionario')?.classList.add('hidden');
}

async function guardarEntradaDiccionario() {
    const editId = document.getElementById('diccionarioEditId')?.value;
    const patron = document.getElementById('diccionarioPatron')?.value.trim();
    const fuente = document.getElementById('diccionarioFuenteEdit')?.value;
    const tipo = document.getElementById('diccionarioTipo')?.value;
    if (!patron) { notify('El patrón es obligatorio', 'error'); return; }

    try {
        const body = { fuente, patron, tipo };
        if (editId) body.id = parseInt(editId);
        const res = await fetch(API + '/diccionario', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (res.ok) {
            notify(editId ? 'Entrada actualizada' : 'Entrada creada', 'success');
            cerrarModalDiccionario();
            cargarDiccionario();
        } else {
            const d = await res.json();
            notify(d.error || 'Error al guardar', 'error');
        }
    } catch (e) {
        notify('Error de conexión', 'error');
    }
}


