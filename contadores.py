"""Corte mensual: lee el contador de las impresoras de ESTA sede por SNMP, lo agrega al CSV
historico de la sede (datos/<sede>.csv) y envia ese CSV por correo.
pip install pysnmp
La sede se define con SEDE en contadores_config.bat; las IPs salen de impresoras.csv (sede,ip).
"""
import asyncio, csv, datetime, os, smtplib, sys
from email.message import EmailMessage
from pysnmp.hlapi.v3arch.asyncio import (SnmpEngine, CommunityData, UdpTransportTarget,
                                         ContextData, ObjectType, ObjectIdentity, get_cmd)

AQUI = os.path.dirname(os.path.abspath(__file__))
SEDE = os.getenv("SEDE", "").strip()
COMUNIDAD = os.getenv("SNMP_COMUNIDAD", "public")
OID_PAGINAS = "1.3.6.1.2.1.43.10.2.1.4.1.1"  # Printer-MIB prtMarkerLifeCount (estandar)
OID_MODELO = "1.3.6.1.2.1.1.1.0"             # sysDescr
COLUMNAS = ["Sede", "IP", "Impresora", "Fecha_Corte", "Contador", "Impresiones_Periodo"]

SMTP_HOST = os.getenv("SMTP_HOST", "sandbox.smtp.mailtrap.io")
SMTP_PORT = int(os.getenv("SMTP_PORT", "2525"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
DESTINO = os.getenv("DESTINO", "esteban.montes@comitedeestudiosmedicos.com")


async def snmp(ip, oid):
    """Valor del OID como texto, o None si la impresora no responde."""
    err, status, _, vbs = await get_cmd(
        SnmpEngine(), CommunityData(COMUNIDAD),
        await UdpTransportTarget.create((ip, 161), timeout=3, retries=1),
        ContextData(), ObjectType(ObjectIdentity(oid)))
    return None if err or status else str(vbs[0][1])


async def leer(ip):
    cont, modelo = await asyncio.gather(snmp(ip, OID_PAGINAS), snmp(ip, OID_MODELO))
    return (modelo or "").splitlines()[0][:60] if modelo else "", cont


def guardar(archivo, lecturas, fecha):
    """Agrega las lecturas [(ip, modelo, contador|None)] al CSV; devuelve las filas nuevas."""
    previo = {}                                  # ip -> ultimo contador valido
    if os.path.exists(archivo):
        with open(archivo, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r["Contador"].isdigit():
                    previo[r["IP"]] = int(r["Contador"])
    filas = []
    for ip, modelo, cont in lecturas:
        ok = cont is not None and cont.isdigit()
        periodo = int(cont) - previo[ip] if ok and ip in previo else ""
        filas.append([SEDE, ip, modelo, fecha, cont if ok else "ERROR", periodo])
    nuevo = not os.path.exists(archivo)
    with open(archivo, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(COLUMNAS)
        w.writerows(filas)
    return filas


async def main():
    with open(os.path.join(AQUI, "impresoras.csv"), encoding="utf-8-sig", newline="") as f:
        ips = [r["ip"].strip() for r in csv.DictReader(f) if r["sede"].strip() == SEDE]
    if not ips:
        sys.exit(f"No hay impresoras para la sede '{SEDE}'. Revisa SEDE en contadores_config.bat e impresoras.csv")
    hoy = datetime.date.today().isoformat()
    datos = await asyncio.gather(*(leer(ip) for ip in ips))
    os.makedirs(os.path.join(AQUI, "datos"), exist_ok=True)
    archivo = os.path.join(AQUI, "datos", SEDE.replace(" ", "_") + ".csv")
    # ponytail: si se ejecuta dos veces el mismo dia agrega dos cortes; deduplicar por fecha si estorba
    filas = guardar(archivo, [(ip, m, c) for ip, (m, c) in zip(ips, datos)], hoy)

    fallas = [r[1] for r in filas if r[4] == "ERROR"]
    cuerpo = "\n".join(f"{r[1]} {r[2]}: {r[4]} (periodo: {r[5] or '-'})" for r in filas)
    if fallas:
        cuerpo += "\n\nSIN RESPUESTA: " + ", ".join(fallas)
    msg = EmailMessage()
    msg["Subject"], msg["To"] = f"Contadores {SEDE} {hoy}", DESTINO
    msg["From"] = SMTP_USER or "contadores@localhost"
    msg.set_content(cuerpo)
    with open(archivo, "rb") as f:
        msg.add_attachment(f.read(), maintype="text", subtype="csv", filename=os.path.basename(archivo))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        if SMTP_USER:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    print(cuerpo)


if __name__ == "__main__":
    asyncio.run(main())
