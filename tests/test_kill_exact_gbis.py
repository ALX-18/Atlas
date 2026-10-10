"""
Sprint G-bis / GB3 — arrêter un processus par son nom EXACT.

L'outil cherchait par morceau de nom (`nom in nom_du_processus`) : confirmer « arrête le
processus e » visait tout processus contenant un « e », et la confirmation n'affichait que
« e ». Désormais :
  - correspondance exacte, avec ou sans « .exe » ;
  - plusieurs correspondances : la confirmation les nomme (PID par PID) ;
  - aucune : rien n'est proposé à la confirmation ;
  - après confirmation, seuls les PID montrés sont arrêtés, et seulement s'ils portent
    toujours ce nom ;
  - les processus système restent refusés (sprint G).

Processus SIMULÉS : aucun vrai processus n'est arrêté.
"""

import asyncio
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import core.intent_engine as ie
from core import confirmation


class FauxProcessus:
    arretes: list = []

    def __init__(self, pid, name):
        self.pid, self._name = pid, name
        self.info = {"pid": pid, "name": name}

    def name(self):
        return self._name

    def terminate(self):
        FauxProcessus.arretes.append((self.pid, self._name))

    def wait(self, timeout=None):
        return 0


MACHINE = [FauxProcessus(10, "notepad.exe"), FauxProcessus(11, "notepad.exe"),
           FauxProcessus(12, "notepad++.exe"), FauxProcessus(13, "steam.exe"),
           FauxProcessus(14, "steamwebhelper.exe"), FauxProcessus(15, "explorer.exe"),
           FauxProcessus(16, "Discord.exe")]


@pytest.fixture
def machine(monkeypatch):
    import psutil

    import tools.process_manager as pm

    FauxProcessus.arretes = []
    par_pid = {p.pid: p for p in MACHINE}
    monkeypatch.setattr(pm.psutil, "process_iter", lambda attrs=None: iter(MACHINE))

    def processus(pid):
        if pid not in par_pid:
            raise psutil.NoSuchProcess(pid)
        return par_pid[pid]

    monkeypatch.setattr(pm.psutil, "Process", processus)
    confirmation._pending.clear()
    yield
    confirmation._pending.clear()


@pytest.mark.parametrize("nom,attendu", [
    ("e", []),
    ("note", []),
    ("steam", [(13, "steam.exe")]),
    ("steam.exe", [(13, "steam.exe")]),
    ("notepad", [(10, "notepad.exe"), (11, "notepad.exe")]),
    ("discord", [(16, "Discord.exe")]),
])
def test_gb3_l_outil_n_arrete_que_le_nom_exact(machine, nom, attendu):
    import tools.process_manager as pm

    pm.kill_process(name=nom)
    assert FauxProcessus.arretes == attendu, f"« {nom} » a arrêté {FauxProcessus.arretes}"


def _demander(nom):
    return ie.request_confirmation("kill_process", {"name": nom}, {}, "arrêter un processus")


def test_gb3_aucune_correspondance_rien_a_confirmer(machine):
    r = _demander("e")
    assert r.get("status") != "confirmation_required", r
    assert confirmation._pending == {}
    assert "e" in r.get("message", "")


def test_gb3_plusieurs_correspondances_sont_nommees(machine):
    r = _demander("notepad")
    assert r.get("status") == "confirmation_required", r
    assert "10" in r["target"] and "11" in r["target"] and "notepad.exe" in r["target"], r["target"]
    assert "notepad++" not in r["target"]


def test_gb3_seuls_les_pid_montres_sont_arretes(machine):
    r = _demander("notepad")
    asyncio.run(ie.execute_confirmed(r["confirmation_id"], {}))
    assert sorted(FauxProcessus.arretes) == [(10, "notepad.exe"), (11, "notepad.exe")]


def test_gb3_un_pid_qui_a_change_de_nom_n_est_pas_arrete(machine, monkeypatch):
    r = _demander("steam")
    MACHINE[3]._name = "autre.exe"      # le PID 13 a été réattribué entre-temps
    try:
        asyncio.run(ie.execute_confirmed(r["confirmation_id"], {}))
    finally:
        MACHINE[3]._name = "steam.exe"
    assert FauxProcessus.arretes == []


@pytest.mark.parametrize("nom", ["explorer", "csrss", "processus winlogon"])
def test_gb3_les_processus_systeme_restent_refuses(machine, nom):
    r = _demander(nom)
    assert r.get("error_code") == "ERR_PROTECTED_PROCESS", r
    assert confirmation._pending == {}
