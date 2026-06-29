# CONCILIACION BANCARIA - VISION EMPRESA

## PRINCIPIO FUNDAMENTAL

La conciliacion bancaria se realiza desde la **VISION DE LA EMPRESA**, no del banco.

## RELACION BANCO - EMPRESA

| Concepto | Vision del Banco | Vision de la Empresa |
|----------|-----------------|---------------------|
| Naturaleza de la cuenta | PASIVO | ACTIVO |
| Deposito / Ingreso | HABER (+ aumento pasivo) | DEBE (+ aumento activo) |
| Cheque / Egreso | DEBE (- disminucion pasivo) | HABER (- disminucion activo) |

## REGLA DE CONVERSION

- DEBE del banco (cargo) → equivale a HABER de la empresa (egreso)
- HABER del banco (abono) → equivale a DEBE de la empresa (ingreso)

## ALMACENAMIENTO DE DATOS

Los movimientos se almacenan TAL CUAL vienen de cada fuente:

- `movimientos_bancarios`: almacenados en VISION DEL BANCO (tal cual llega el extracto)
- `movimientos_contables`: almacenados en VISION DE LA EMPRESA (tal cual estan en los libros)

La conversion logica se realiza unicamente en el servicio de conciliacion (`ConciliadorBancario`).

## PARTIDAS CONCILIATORIAS (VISION EMPRESA)

Las partidas se clasifican segun el saldo que afectan:

| Partida | Origen | Afecta a | Ajuste desde origen |
|---------|--------|----------|-------------------|
| Cheque no debitado | Contabilidad (HABER) | Banco | RESTAR del saldo del banco |
| Deposito no acreditado | Contabilidad (DEBE) | Banco | SUMAR al saldo del banco |
| Nota debito no registrada | Banco (DEBE) | Contabilidad | RESTAR del saldo contable |
| Nota credito no registrada | Banco (HABER) | Contabilidad | SUMAR al saldo contable |

### Clasificacion por tipo

- **Transitoria**: Se resuelve con el tiempo (cheques no debitados, depositos no acreditados)
- **Permanente**: Requiere ajuste contable (comisiones, intereses, errores)

## FORMULAS DE CONCILIACION

### Forma 1: Desde saldo banco

```
Saldo segun banco          X
(-) Cheques no debitados   (A)    → afectan al banco
(+) Depositos no acred.     B     → afectan al banco
= Saldo banco ajustado     X-A+B

Saldo segun contabilidad   Y
(-) Notas debito no reg.   (C)    → afectan a contabilidad
(+) Notas credito no reg.   D     → afectan a contabilidad
= Saldo contab. ajustado   Y-C+D

Verificacion: X-A+B = Y-C+D (conciliado)
```

### Forma 2: Desde saldo contabilidad

```
Saldo segun contabilidad   Y
(-) Notas debito no reg.   (C)    → afectan a contabilidad
(+) Notas credito no reg.   D     → afectan a contabilidad
= Saldo contab. ajustado   Y-C+D

Saldo segun banco          X
(-) Cheques no debitados   (A)    → afectan al banco
(+) Depositos no acred.     B     → afectan al banco
= Saldo banco ajustado     X-A+B

Verificacion: Y-C+D = X-A+B (conciliado)
```

### Conciliacion Cuadrada

```
Saldo banco inicial + movimientos banco = Saldo banco final
Saldo contable inicial + movimientos contables = Saldo contable final

Partidas del periodo: cheque, depositos, nd, nc

Saldo banco ajustado = Saldo banco final - cheques + depositos
Saldo contable ajustado = Saldo contable final - nd + nc

Verificar: Saldo banco ajustado = Saldo contable ajustado
```
