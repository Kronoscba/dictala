"""Tests del lockfile: la segunda instancia tiene que salir, no esperar."""

from __future__ import annotations

from dictala import lock


def test_toma_el_lock(tmp_path):
    ruta = str(tmp_path / "dictala.lock")
    tomado = lock.tomar(ruta)
    assert tomado is not None
    tomado.liberar()


def test_segunda_instancia_falla(tmp_path):
    ruta = str(tmp_path / "dictala.lock")
    primero = lock.tomar(ruta)
    segundo = lock.tomar(ruta)
    assert primero is not None
    assert segundo is None, "la segunda instancia tiene que salir, no esperar"
    primero.liberar()


def test_liberado_se_puede_volver_a_tomar(tmp_path):
    ruta = str(tmp_path / "dictala.lock")
    lock.tomar(ruta).liberar()
    segundo = lock.tomar(ruta)
    assert segundo is not None
    segundo.liberar()


def test_lock_independiente_por_ruta(tmp_path):
    a = lock.tomar(str(tmp_path / "a.lock"))
    b = lock.tomar(str(tmp_path / "b.lock"))
    assert a is not None and b is not None
    a.liberar()
    b.liberar()


def test_escribe_el_pid(tmp_path):
    """El pid queda en el archivo: sirve para diagnosticar instancias colgadas."""
    import os

    ruta = tmp_path / "dictala.lock"
    tomado = lock.tomar(str(ruta))
    assert tomado is not None
    contenido = ruta.read_text()
    assert str(os.getpid()) in contenido
    tomado.liberar()


def test_ruta_no_escribible_devuelve_none(tmp_path):
    """Un lock que no se puede tomar no debe romper el dictado."""
    taken = lock.tomar(str(tmp_path / "no-existe" / "sub" / "x.lock"))
    assert taken is None
