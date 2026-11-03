#!/usr/bin/env python3
"""Script minimaliste, indépendant d'Odoo : récupère les fiches employés et les congés depuis Lucca.

Deux API Lucca sont nécessaires (cf. https://developers.luccasoftware.com) :

 - Employés : Lucca API v5 (`/lucca-api/employees`), authentification OAuth2 client credentials
   (token obtenu sur accounts.world.luccasoftware.com), scope `employees.readonly`,
   en-tête `Api-Version: 2024-11-01`, pagination par curseur (`links.next.cursor`).

 - Congés : la v5 n'expose pas (encore) les congés. On utilise l'API legacy v3
   (`/api/v3/leaves`), pagination `paging={offset},{limit}`. Les filtres `date` et
   `leavePeriod.ownerId` sont obligatoires. L'`ownerId` v3 est le même identifiant que
   l'`id` employé v5 (en entier côté v3, en chaîne côté v5).
   Authentification documentée : clé API legacy (`Authorization: lucca application=...`),
   créée dans les paramètres du compte Lucca, distincte du client OAuth2
   (https://support.lucca.fr/hc/en-us/articles/115000084851). Si LUCCA_API_KEY n'est pas
   fournie, le script tente le token OAuth2 (`Bearer`) sur la v3 : ce n'est pas documenté,
   un 401 signifie qu'il faut créer une clé API.

Configuration par variables d'environnement :

    LUCCA_HOST           ex. https://monentreprise.ilucca.net (ou ilucca-test / sandbox)
    LUCCA_CLIENT_ID      client OAuth2 (déclaré dans Lucca : /identity/admin/integration-keys)
    LUCCA_CLIENT_SECRET  secret OAuth2
    LUCCA_API_KEY        (optionnel) clé API legacy v3 pour les congés, cf. ci-dessus

Usage :

    python3 lucca_api_fetch.py                       # employés + congés de l'année en cours
    python3 lucca_api_fetch.py --from 2026-01-01 --to 2026-12-31
    python3 lucca_api_fetch.py --employees-only
    python3 lucca_api_fetch.py --json export.json    # dump complet en JSON
"""

import argparse
import datetime
import json
import os
import sys

import requests

TOKEN_URL = "https://accounts.world.luccasoftware.com/connect/token"
API_VERSION = "2024-11-01"
TIMEOUT = 60


class LuccaClient:
    def __init__(self, host, client_id=None, client_secret=None, api_key=None):
        self.host = host.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_key = api_key
        self._token = None

    # ------------------------------------------------------------------ v5 (OAuth2)
    def get_access_token(self, scope="employees.readonly"):
        if not self.client_id or not self.client_secret:
            sys.exit("LUCCA_CLIENT_ID / LUCCA_CLIENT_SECRET manquants (API v5).")
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": scope,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]  # valable 30 min
        return self._token

    def _v5_headers(self):
        if not self._token:
            self.get_access_token()
        return {
            "Authorization": "Bearer %s" % self._token,
            "Api-Version": API_VERSION,
            "Accept": "application/json",
        }

    def v5_list(self, path, params=None):
        """Itère sur tous les items d'une collection v5 en suivant les curseurs de pagination."""
        params = dict(params or {})
        params.setdefault("limit", 1000)
        params["include"] = ",".join(sorted(set(params.get("include", "").split(",")) | {"links"} - {""}))
        url = "%s%s" % (self.host, path)
        while url:
            resp = requests.get(url, params=params, headers=self._v5_headers(), timeout=TIMEOUT)
            resp.raise_for_status()
            body = resp.json()
            yield body
            nxt = (body.get("links") or {}).get("next")
            if not nxt:
                break
            url, params = nxt["href"], None  # href contient déjà page=, limit=, include=

    def fetch_employees(self, status=None):
        """Fiches employés v5 + ressources liées (employment, job-position) via include=embedded."""
        params = {"include": "embedded,totalCount"}
        if status:
            params["status"] = status  # active, upcoming, deactivated
        employees, embedded = [], {}
        for page in self.v5_list("/lucca-api/employees", params):
            employees.extend(page.get("items", []))
            for rtype, by_id in (page.get("embedded") or {}).items():
                embedded.setdefault(rtype, {}).update(by_id)
        for emp in employees:
            for key, rtype in (("applicableEmployment", "employment"), ("applicableJobPosition", "job-position")):
                ref = emp.get(key) or {}
                full = embedded.get(rtype, {}).get(ref.get("id"))
                if full:
                    emp[key] = full
        return employees

    # ------------------------------------------------------------------ v3 (clé API)
    def _v3_headers(self):
        if self.api_key:
            auth = "lucca application=%s" % self.api_key
        else:
            # Non documenté : on tente le token OAuth2 v5 sur l'API legacy.
            auth = "Bearer %s" % (self._token or self.get_access_token())
        return {"Authorization": auth, "Accept": "application/json"}

    def v3_list(self, path, params=None, page_size=1000):
        """Itère sur tous les items d'une collection v3 (pagination par offset)."""
        params = dict(params or {})
        offset = 0
        while True:
            params["paging"] = "%d,%d" % (offset, page_size)
            resp = requests.get("%s%s" % (self.host, path), params=params, headers=self._v3_headers(), timeout=TIMEOUT)
            if resp.status_code in (401, 403) and not self.api_key:
                sys.exit(
                    "L'API legacy v3 (%s) refuse le token OAuth2 (HTTP %d). Il faut créer une clé API "
                    "legacy dans Lucca et la fournir via LUCCA_API_KEY : "
                    "https://support.lucca.fr/hc/en-us/articles/115000084851" % (path, resp.status_code)
                )
            resp.raise_for_status()
            items = resp.json().get("data", {}).get("items", [])
            yield from items
            if len(items) < page_size:
                break
            offset += page_size

    def fetch_leaves(self, employee_ids, date_from, date_to, chunk_size=50):
        """Congés (demi-journées) des employés donnés sur la période [date_from, date_to]."""
        fields = ",".join([
            "id", "date", "isAm", "value", "isActive", "creationDate", "cancellationDate", "comment",
            "leaveAccountId", "leaveAccount[id,name]",
            "leavePeriodId", "leavePeriod[id,ownerId,isConfirmed,confirmationDate]",
        ])
        leaves = []
        ids = [str(i) for i in employee_ids]
        for i in range(0, len(ids), chunk_size):
            params = {
                "date": "between,%s,%s" % (date_from, date_to),
                "leavePeriod.ownerId": ",".join(ids[i:i + chunk_size]),
                "fields": fields,
            }
            leaves.extend(self.v3_list("/api/v3/leaves", params))
        return leaves


def main():
    today = datetime.date.today()
    parser = argparse.ArgumentParser(description="Récupère employés et congés depuis Lucca.")
    parser.add_argument("--from", dest="date_from", default=today.replace(month=1, day=1).isoformat())
    parser.add_argument("--to", dest="date_to", default=today.replace(month=12, day=31).isoformat())
    parser.add_argument("--status", default=None, help="active, upcoming ou deactivated (défaut : tous)")
    parser.add_argument("--employees-only", action="store_true")
    parser.add_argument("--json", metavar="FICHIER", help="écrit le résultat complet en JSON")
    args = parser.parse_args()

    host = os.environ.get("LUCCA_HOST")
    if not host:
        sys.exit("LUCCA_HOST manquant (ex. https://monentreprise.ilucca.net).")
    client = LuccaClient(
        host,
        client_id=os.environ.get("LUCCA_CLIENT_ID"),
        client_secret=os.environ.get("LUCCA_CLIENT_SECRET"),
        api_key=os.environ.get("LUCCA_API_KEY"),
    )

    employees = client.fetch_employees(status=args.status)
    print("%d employé(s)" % len(employees))
    for emp in employees:
        employment = emp.get("applicableEmployment") or {}
        print("  [%s] %s %s <%s> %s  %s -> %s" % (
            emp.get("id"), emp.get("givenName"), emp.get("familyName"), emp.get("email"), emp.get("status"),
            (employment.get("start") or {}).get("date", "?"), (employment.get("end") or {}).get("date", ""),
        ))

    leaves = []
    if not args.employees_only:
        leaves = client.fetch_leaves([e["id"] for e in employees], args.date_from, args.date_to)
        print("%d congé(s) (demi-journées) du %s au %s" % (len(leaves), args.date_from, args.date_to))
        for lv in leaves:
            period = lv.get("leavePeriod") or {}
            print("  [%s] owner=%s %s %s %s%s  période=%s%s" % (
                lv.get("id"), period.get("ownerId"), lv.get("date"), "AM" if lv.get("isAm") else "PM",
                (lv.get("leaveAccount") or {}).get("name"),
                "" if lv.get("isActive", True) else " (ANNULÉ)",
                lv.get("leavePeriodId"), "" if period.get("isConfirmed", True) else " (EN ATTENTE)",
            ))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"employees": employees, "leaves": leaves}, f, ensure_ascii=False, indent=2)
        print("Export écrit dans %s" % args.json)


if __name__ == "__main__":
    main()
