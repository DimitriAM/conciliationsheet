<div class="upload-grid">
    <div class="card">
        <h2>Extracto Bancario</h2>
        <p style="font-size:0.85rem;color:#666;margin-bottom:1rem;">Movimientos del banco (débitos/créditos).</p>
        <div class="drop-zone" id="dropZoneBanco">
            <div class="icon"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#888" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg></div>
            <p>Arrastra el extracto bancario aquí o haz clic para seleccionar</p>
            <p style="font-size:0.8rem;color:#aaa;margin-top:0.3rem;">Excel (.xlsx, .xls) o CSV</p>
        </div>
        <input type="file" id="fileInputBanco" accept=".xlsx,.xls,.csv" style="display:none">
        <ul class="file-list" id="fileListBanco"></ul>
        <div class="flex gap-1" style="margin-top:1rem;">
            <div class="form-group" style="flex:1;">
                <label for="saldoInicialBanco">Saldo Inicial</label>
                <input type="number" id="saldoInicialBanco" step="0.01" placeholder="0.00">
            </div>
            <div class="form-group" style="flex:1;">
                <label for="saldoFinalBanco">Saldo Final</label>
                <input type="number" id="saldoFinalBanco" step="0.01" placeholder="0.00">
            </div>
        </div>
        <div class="mt-2">
            <button class="btn btn-primary" id="btnUploadBanco" disabled>Subir</button>
            <span id="statusBanco"></span>
        </div>
    </div>

    <div class="card">
        <h2>Movimientos Contables</h2>
        <p style="font-size:0.85rem;color:#666;margin-bottom:1rem;">Registros internos de la empresa (ingresos/egresos).</p>
        <div class="drop-zone" id="dropZoneContable">
            <div class="icon"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#888" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg></div>
            <p>Arrastra los movimientos contables aquí o haz clic para seleccionar</p>
            <p style="font-size:0.8rem;color:#aaa;margin-top:0.3rem;">Excel (.xlsx, .xls) o CSV</p>
        </div>
        <input type="file" id="fileInputContable" accept=".xlsx,.xls,.csv" style="display:none">
        <ul class="file-list" id="fileListContable"></ul>
        <div class="flex gap-1" style="margin-top:1rem;">
            <div class="form-group" style="flex:1;">
                <label for="saldoInicialContable">Saldo Inicial</label>
                <input type="number" id="saldoInicialContable" step="0.01" placeholder="0.00">
            </div>
            <div class="form-group" style="flex:1;">
                <label for="saldoFinalContable">Saldo Final</label>
                <input type="number" id="saldoFinalContable" step="0.01" placeholder="0.00">
            </div>
        </div>
        <div class="mt-2">
            <button class="btn btn-primary" id="btnUploadContable" disabled>Subir</button>
            <span id="statusContable"></span>
        </div>
    </div>
</div>

<div class="card" id="archivosCard">
    <div class="flex-between">
        <h2>Archivos Subidos</h2>
        <button class="btn btn-secondary" id="btnRefreshArchivos" style="font-size:0.85rem;">Actualizar</button>
    </div>
    <div id="archivosList"><p style="color:#888;">No hay archivos subidos.</p></div>
</div>

<div class="card" id="diccionarioCard">
    <div class="flex-between">
        <h2>Diccionario de Sinónimos</h2>
        <div class="flex gap-1">
            <select id="diccionarioFuente" style="padding:0.4rem 0.8rem;border:1px solid #d0d0e0;border-radius:8px;">
                <option value="banco">Banco</option>
                <option value="contabilidad">Contabilidad</option>
            </select>
            <button class="btn btn-secondary" id="btnRefrescarDiccionario" style="font-size:0.85rem;">Actualizar</button>
            <button class="btn btn-primary" id="btnNuevaEntrada" style="font-size:0.85rem;">+ Nueva</button>
        </div>
    </div>
    <p style="font-size:0.85rem;color:#666;margin-bottom:0.8rem;">
        Patrones aprendidos automáticamente al procesar archivos. Se usan para matchear descripciones entre banco y contabilidad. También podés agregar o eliminar entradas manualmente.
    </p>
    <div id="diccionarioList"><p style="color:#888;">Cargando...</p></div>
</div>

<div class="modal-overlay hidden" id="modalDiccionario">
    <div class="modal-card">
        <h3 id="modalDiccionarioTitle">Nueva Entrada</h3>
        <input type="hidden" id="diccionarioEditId" value="">
        <div class="form-group">
            <label for="diccionarioFuenteEdit">Fuente</label>
            <select id="diccionarioFuenteEdit">
                <option value="banco">Banco</option>
                <option value="contabilidad">Contabilidad</option>
            </select>
        </div>
        <div class="form-group">
            <label for="diccionarioPatron">Patrón (palabra clave en la descripción)</label>
            <input type="text" id="diccionarioPatron" placeholder="Ej: cheq, transf, acreditacion">
        </div>
        <div class="form-group">
            <label for="diccionarioTipo">Tipo canónico</label>
            <select id="diccionarioTipo">
                <option value="cheque">Cheque</option>
                <option value="deposito">Depósito</option>
                <option value="nota_debito">Nota de Débito</option>
                <option value="nota_credito">Nota de Crédito</option>
                <option value="comision">Comisión</option>
                <option value="interes">Interés</option>
                <option value="transferencia">Transferencia</option>
                <option value="saldo_inicial">Saldo Inicial</option>
            </select>
        </div>
        <div class="flex gap-1" style="justify-content:flex-end;margin-top:1rem;">
            <button class="btn btn-secondary" id="btnCancelarDiccionario" type="button">Cancelar</button>
            <button class="btn btn-primary" id="btnGuardarDiccionario" type="button">Guardar</button>
        </div>
    </div>
</div>
