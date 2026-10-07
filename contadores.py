"""Lee el contador de paginas de impresoras por SNMP y lo envia a un buzon sandbox.
pip install pysnmp
Uso: python contadores.py            (agendar con schtasks, ver abajo)
"""
import asyncio, os, smtplib, datetime
from email.message import EmailMessage
from pysnmp.hlapi.v3arch.asyncio import (SnmpEngine, CommunityData, UdpTransportTarget,
                                         ContextData, ObjectType, ObjectIdentity, get_cmd)

IMPRESORAS = {"Recepcion": "192.168.1.50", "Contabilidad": "192.168.1.51"}  # nombre: IP
COMUNIDAD = "public"
OID_PAGINAS = "1.3.6.1.2.1.43.10.2.1.4.1.1"  # Printer-MIB prtMarkerLifeCount (estandar)

# SMTP sandbox: Mailtrap (sandbox.smtp.mailtrap.io:2525 + user/pass) o MailHog/Papercut (localhost:1025 sin login)
SMTP_HOST = os.getenv("SMTP_HOST", "sandbox.smtp.mailtrap.io")
SMTP_PORT = int(os.getenv("SMTP_PORT", "2525"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
DESTINO = "eduard.munoz@comitedeestudiosmedicos.com"


async def contador(ip):
    err, status, _, vbs = await get_cmd(
        SnmpEngine(), CommunityData(COMUNIDAD),
        await UdpTransportTarget.create((ip, 161), timeout=3, retries=1),
        ContextData(), ObjectType(ObjectIdentity(OID_PAGINAS)))
    if err or status:
        return f"ERROR: {err or status.prettyPrint()}"
    return str(vbs[0][1])


async def main():
    hoy = datetime.date.today().isoformat()
    vals = await asyncio.gather(*(contador(ip) for ip in IMPRESORAS.values()))
    cuerpo = "\n".join(f"{n} ({ip}): {v}" for (n, ip), v in zip(IMPRESORAS.items(), vals))
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = f"Contadores impresoras {hoy}", "contadores@localhost", DESTINO
    msg.set_content(cuerpo)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        if SMTP_USER:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    print(cuerpo)


asyncio.run(main())

# Agendar en una fecha concreta (una sola vez), en PowerShell/cmd:
#   schtasks /create /tn ContadoresImpresoras /sc once /sd 31/10/2026 /st 18:00 /tr "python C:\ruta\contadores.py"
# (formato de /sd depende de la configuracion regional de Windows)
