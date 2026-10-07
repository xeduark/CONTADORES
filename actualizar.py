"""Actualiza el programa desde GitHub (git pull) antes de cada uso.

    python actualizar.py              # lo llama CONTADORES.bat: baja la ultima version, si puede
    python actualizar.py --instalar   # lo llama INSTALAR.bat: deja lista la conexion de esta PC

La conexion usa una llave SSH propia de esta PC, de solo lectura ("deploy key" en GitHub): si
la PC se pierde, se borra esa llave en GitHub y listo. Va por un remoto aparte ("actualizar"),
asi en la PC de desarrollo el "origin" con el que se suben cambios queda igual.
Si no hay internet o algo falla, sigue con la version que ya tiene: actualizar nunca impide
enviar los contadores.
"""
import os
import shutil
import socket
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = "git@github.com:xeduark/CONTADORES.git"
RAMA = "main"
REMOTO = "actualizar"
LLAVE = os.path.join(os.path.expanduser("~"), ".ssh", "contadores_github")


def _git_exe():
    """Ruta de git.exe, aunque recien instalado todavia no este en el PATH."""
    ruta = r"C:\Program Files\Git\cmd\git.exe"
    return shutil.which("git") or (ruta if os.path.exists(ruta) else None)


def _git(carpeta, *args, timeout=90):
    return subprocess.run([_git_exe(), "-C", carpeta, *args],
                          capture_output=True, text=True, timeout=timeout)


def actualizar(carpeta=AQUI, remoto=REMOTO, rama=RAMA):
    """Baja la ultima version. Devuelve True si cambio algo."""
    if not _git_exe() or not os.path.isdir(os.path.join(carpeta, ".git")):
        print("Actualizacion automatica sin configurar (se configura con INSTALAR.bat).")
        return False
    try:
        antes = _git(carpeta, "rev-parse", "HEAD").stdout.strip()
        pull = _git(carpeta, "pull", "--ff-only", "--quiet", remoto, rama)
    except (subprocess.TimeoutExpired, OSError):
        pull = None
    if pull is None or pull.returncode:
        print("No se pudo buscar actualizaciones (sin internet o sin acceso). "
              "Se usa la version actual.")
        return False
    despues = _git(carpeta, "rev-parse", "HEAD").stdout.strip()
    if antes == despues:
        print("El programa esta al dia.")
        return False
    print("Programa actualizado a la ultima version.")
    if "requirements.txt" in _git(carpeta, "diff", "--name-only", antes, despues).stdout.split():
        print("Instalando librerias nuevas...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                        "--disable-pip-version-check", "-r",
                        os.path.join(carpeta, "requirements.txt")])
    return True


def instalar(carpeta=AQUI):
    """Configura la llave y el remoto de esta PC. Devuelve True si ya puede actualizarse."""
    git = _git_exe()
    if not git:
        print("Falta Git: vuelve a abrir INSTALAR.bat (lo instala).")
        return False
    nueva = not os.path.isdir(os.path.join(carpeta, ".git"))
    if nueva:                                  # carpeta copiada sin el historial
        _git(carpeta, "init", "-q")
    if REMOTO in _git(carpeta, "remote").stdout.split():
        _git(carpeta, "remote", "set-url", REMOTO, REPO)
    else:
        _git(carpeta, "remote", "add", REMOTO, REPO)

    compartida = os.path.join(carpeta, "llave_compartida")
    if os.path.exists(compartida):   # misma llave para todas las PC: viaja en la carpeta, no por git
        os.makedirs(os.path.dirname(LLAVE), exist_ok=True)
        shutil.copyfile(compartida, LLAVE)             # siempre pisa: asi se renueva
        shutil.copyfile(compartida + ".pub", LLAVE + ".pub")
    if not os.path.exists(LLAVE):
        os.makedirs(os.path.dirname(LLAVE), exist_ok=True)
        keygen = shutil.which("ssh-keygen") or os.path.join(
            os.path.dirname(os.path.dirname(git)), "usr", "bin", "ssh-keygen.exe")
        subprocess.run([keygen, "-t", "ed25519", "-N", "", "-q", "-f", LLAVE,
                        "-C", f"contadores-{socket.gethostname()}"], check=True)
    llave = LLAVE.replace("\\", "/")
    _git(carpeta, "config", "core.sshCommand",
         f'ssh -i "{llave}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new '
         f"-o ConnectTimeout=15")

    try:
        acceso = _git(carpeta, "ls-remote", REMOTO, RAMA).returncode == 0
    except subprocess.TimeoutExpired:
        acceso = False
    if not acceso:
        with open(LLAVE + ".pub", encoding="utf-8") as f:
            publica = f.read().strip()
        subprocess.run("clip", input=publica, text=True, shell=True)
        print("\nFALTA AUTORIZAR ESTA PC en GitHub (una sola vez). La llave ya quedo copiada:\n"
              "  1. Abre https://github.com/xeduark/CONTADORES/settings/keys\n"
              "  2. Clic en 'Add deploy key'.\n"
              f"  3. Title: {socket.gethostname()}   Key: pega (Ctrl+V).\n"
              "  4. NO marques 'Allow write access'. Clic en 'Add key'.\n"
              "  5. Vuelve a abrir INSTALAR.bat.\n"
              f"\nLlave de esta PC:\n{publica}\n")
        return False

    if nueva:   # dejar la carpeta exactamente en la version del repo
        _git(carpeta, "fetch", "-q", REMOTO, RAMA)
        _git(carpeta, "checkout", "-q", "-f", "-B", RAMA, f"{REMOTO}/{RAMA}")
    else:
        actualizar(carpeta)
    print("Actualizacion automatica lista.")
    return True


if __name__ == "__main__":
    if "--instalar" in sys.argv:
        sys.exit(0 if instalar() else 1)
    actualizar()
