"""
Sprint Compétences 1 / CP5 — le Bluetooth, par l'API Windows des radios (WinRT, sans outil tiers).

- Allumer, éteindre : `Windows.Devices.Radios` ; l'état est RELU après coup.
- Avant d'éteindre : un clavier ou une souris Bluetooth connecté est signalé (le moteur demande
  alors confirmation — Alexis pourrait perdre la main sur son PC).
- Connecter un appareil appairé : Windows n'offre pas d'API propre pour connecter un casque ou une
  enceinte depuis un programme de bureau (mesuré, rapport Compétences 1) ; Atlas le dit et ouvre les
  paramètres Bluetooth.
- PC sans radio Bluetooth : dit.

`MATERIEL` est la seule porte vers Windows ; les tests la remplacent.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Callable, Optional


def _executer(coro_fabrique: Callable):
    """Exécute une coroutine WinRT dans une boucle à part (le serveur a déjà la sienne)."""
    sortie: dict = {}

    def fil():
        try:
            sortie["v"] = asyncio.run(coro_fabrique())
        except BaseException as e:         # noqa: BLE001
            sortie["e"] = e

    t = threading.Thread(target=fil, name="atlas-bluetooth", daemon=True)
    t.start()
    t.join(20)
    if "e" in sortie:
        raise sortie["e"]
    if "v" not in sortie:
        raise TimeoutError("Windows ne répond pas (Bluetooth)")
    return sortie["v"]


# Classe d'appareil Bluetooth « classique » : majeur 5 = périphérique ; bits 6-7 du mineur :
# 1 clavier, 2 pointeur, 3 les deux. BLE : apparence 15 (HID), sous-catégorie 1 clavier, 2 souris.
def _saisie_classique(brut: int) -> Optional[str]:
    if (brut >> 8) & 0x1F != 5:
        return None
    return {1: "clavier", 2: "souris", 3: "clavier et souris"}.get((brut >> 6) & 0x3)


def _saisie_le(categorie: int, sous: int) -> Optional[str]:
    if categorie != 15:
        return None
    return {1: "clavier", 2: "souris"}.get(sous)


class Materiel:
    async def _radios(self):
        from winrt.windows.devices.radios import Radio, RadioKind

        return [r for r in await Radio.get_radios_async() if r.kind == RadioKind.BLUETOOTH]

    def etat(self) -> Optional[str]:
        """« allume », « eteint », « indisponible » (radio coupée par le matériel), ou None (pas de radio)."""
        async def f():
            from winrt.windows.devices.radios import RadioState

            radios = await self._radios()
            if not radios:
                return None
            s = radios[0].state
            return {RadioState.ON: "allume", RadioState.OFF: "eteint"}.get(s, "indisponible")
        return _executer(f)

    def regler(self, allume: bool) -> str:
        """Rend l'issue de la demande à Windows : « ok », « refuse », « pas_de_radio », etc."""
        async def f():
            from winrt.windows.devices.radios import Radio, RadioAccessStatus, RadioState

            acces = await Radio.request_access_async()
            if acces != RadioAccessStatus.ALLOWED:
                return f"acces_{int(acces)}"
            radios = await self._radios()
            if not radios:
                return "pas_de_radio"
            r = await radios[0].set_state_async(RadioState.ON if allume else RadioState.OFF)
            return "ok" if int(r) == 1 else f"refuse_{int(r)}"
        return _executer(f)

    def appaires(self) -> list[dict]:
        """Les appareils appairés : nom, connecté, et s'il s'agit d'un clavier ou d'une souris."""
        async def f():
            from winrt.windows.devices.bluetooth import BluetoothDevice, BluetoothLEDevice
            from winrt.windows.devices.enumeration import DeviceInformation

            out = []
            for d in await DeviceInformation.find_all_async_aqs_filter(
                    BluetoothDevice.get_device_selector_from_pairing_state(True)):
                item = {"nom": d.name, "sorte": "classique", "connecte": None, "saisie": None, "id": d.id}
                try:
                    bd = await BluetoothDevice.from_id_async(d.id)
                    item["connecte"] = int(bd.connection_status) == 1
                    item["saisie"] = _saisie_classique(int(bd.class_of_device.raw_value))
                except OSError:
                    item["connecte"] = False      # « pas prêt » : adaptateur absent ou appareil hors de portée
                out.append(item)
            for d in await DeviceInformation.find_all_async_aqs_filter(
                    BluetoothLEDevice.get_device_selector_from_pairing_state(True)):
                item = {"nom": d.name, "sorte": "le", "connecte": None, "saisie": None, "id": d.id}
                try:
                    bd = await BluetoothLEDevice.from_id_async(d.id)
                    item["connecte"] = int(bd.connection_status) == 1
                    item["saisie"] = _saisie_le(int(bd.appearance.category), int(bd.appearance.subcategory))
                except OSError:
                    item["connecte"] = False
                out.append(item)
            return out
        return _executer(f)

    def ouvrir_parametres(self) -> bool:
        import os

        os.startfile("ms-settings:bluetooth")
        return True


MATERIEL = Materiel()


def etat() -> Optional[str]:
    return MATERIEL.etat()


def saisie_connectee() -> list[dict]:
    """Les claviers et souris Bluetooth connectés en ce moment."""
    return [a for a in MATERIEL.appaires() if a["connecte"] and a["saisie"]]


def regler(allume: bool) -> dict:
    """{"avant", "issue", "apres"} — « apres » est RELU après la demande."""
    avant = MATERIEL.etat()
    if avant is None:
        return {"avant": None, "issue": "pas_de_radio", "apres": None}
    issue = MATERIEL.regler(allume)
    apres = MATERIEL.etat()
    return {"avant": avant, "issue": issue, "apres": apres}


def trouver_appaire(nom: str) -> list[dict]:
    from core.horloge import plat

    voulu = plat(nom).strip()
    vus, uniques = set(), []
    for a in MATERIEL.appaires():
        if a["nom"] not in vus:
            vus.add(a["nom"])
            uniques.append(a)
    # « mon casque JBL » : les mots génériques ne nomment pas l'appareil, « jbl » oui.
    mots = [m for m in voulu.replace("-", " ").split() if m not in _GENERIQUES]
    if not mots:
        return uniques
    return [a for a in uniques if all(m in plat(a["nom"]) for m in mots) or plat(a["nom"]) in voulu]


_GENERIQUES = {"mon", "ma", "mes", "le", "la", "les", "l'", "casque", "ecouteurs", "ecouteur", "enceinte", "oreillettes",
               "appareil", "peripherique", "bluetooth", "audio", "sans", "fil"}


def diagnostic() -> dict:
    try:
        e = MATERIEL.etat()
        return {"ok": e is not None, "etat": e or "aucune radio Bluetooth vue par Windows"}
    except Exception as ex:
        return {"ok": False, "etat": f"{type(ex).__name__}: {ex}"}
