#!/bin/sh
# One-time (safe-to-re-run) PopHeat setup, run inside the IRIS container:
#   docker compose exec iris sh /irisdev/app/docker/init-production.sh
#
# Steps (D-05): install iop + tzdata -> ensure the POPHEAT namespace exists
# (D-04 fallback in case merge.cpf didn't take effect) -> compile the two
# Persistent classes -> `iop --init` the IOP support classes into POPHEAT
# (required once per namespace before the first `iop --migrate` -- omitting
# it fails registration with "IRIS could not find a class required during
# component registration") -> migrate settings.py -> enable auto-start ->
# start the production for this run too (SetAutoStart only affects the NEXT
# instance start).
set -e

IRIS_INSTANCE="IRIS"
IRIS_NAMESPACE="POPHEAT"
APP_DIR="/irisdev/app"
export IRISNAMESPACE="$IRIS_NAMESPACE"
export PATH="$PATH:/home/irisowner/.local/bin"

echo "=== PopHeat: installing iris-pex-embedded-python + tzdata ==="
pip3 install --quiet --break-system-packages iris-pex-embedded-python tzdata

echo "=== PopHeat: verifying the ${IRIS_NAMESPACE} namespace exists (D-04) ==="
# WR-03: grep for the literal "NS_EXISTS=" marker prefix rather than any bare
# 0/1 digit -- a bare-digit grep is fragile to incidental digits elsewhere in
# the session transcript (login banner, version string, warning), which could
# silently mis-parse the exists/not-exists result.
NS_EXISTS=$(iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF 2>&1 | grep -o 'NS_EXISTS=[01]' | tail -1 | cut -d= -f2
write "NS_EXISTS=",##class(Config.Namespaces).Exists("${IRIS_NAMESPACE}"),!
halt
IRISEOF
)

if [ "$NS_EXISTS" != "1" ]; then
  echo "=== PopHeat: ${IRIS_NAMESPACE} missing after merge.cpf -- creating imperatively ==="
  iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF
set dbDir = "/usr/irissys/mgr/popheat"
set dbProps("Directory") = dbDir
set sc = ##class(Config.Databases).Create(dbDir, .dbProps)
if 'sc { do \$System.Status.DisplayError(sc) }
set nsProps("Globals") = "${IRIS_NAMESPACE}"
set nsProps("Routines") = "${IRIS_NAMESPACE}"
set sc = ##class(Config.Namespaces).Create("${IRIS_NAMESPACE}", .nsProps)
if 'sc { do \$System.Status.DisplayError(sc) }
halt
IRISEOF
fi

echo "=== PopHeat: setting the _SYSTEM password (for Management Portal / debugging access) ==="
iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF
set Properties("Password") = "adm"
set sc = ##class(Security.Users).Modify("_SYSTEM", .Properties)
if 'sc { do \$System.Status.DisplayError(sc) }
do ##class(Security.Users).UnExpireUserPasswords("_SYSTEM")
halt
IRISEOF

echo "=== PopHeat: resolving the ${IRIS_NAMESPACE} database resource (for public read access) ==="
# Unauthenticated (AutheEnabled=64) requests run as UnknownUser, which ships
# with zero privileges. Getting *past authentication* is not the same as
# getting *past authorization*: without READ on the database backing the
# POPHEAT namespace, IRIS cannot even execute the dispatch class and answers
# 403. The needed privilege is carried by the auto-created role whose name
# equals that database's resource name (e.g. %DB_%DEFAULT in this image --
# the POPHEAT database does NOT necessarily use a %DB_POPHEAT resource, so
# resolve it at runtime rather than hardcoding it).
DB_RESOURCE=$(iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF 2>&1 | grep -o 'DB_RESOURCE=[^ ]*' | tail -1 | cut -d= -f2-
set res = ""
set db = ""
set nsSc = ##class(Config.Namespaces).Get("${IRIS_NAMESPACE}", .nsProps)
if nsSc { set dbSc = ##class(Config.Databases).Get(nsProps("Globals"), .dbProps) }
if \$data(dbProps("Directory")) { set db = ##class(SYS.Database).%OpenId(dbProps("Directory")) }
if \$isobject(db) { set res = db.ResourceName }
write "DB_RESOURCE=",res,!
halt
IRISEOF
)
if [ -z "$DB_RESOURCE" ]; then
  DB_RESOURCE="%DB_%DEFAULT"
  echo "    (could not resolve it dynamically -- falling back to ${DB_RESOURCE})"
fi
echo "    ${IRIS_NAMESPACE} database resource: ${DB_RESOURCE}"

echo "=== PopHeat: registering /csp/popheat/api web application (PopHeat.API, unauthenticated per D-06) ==="
# Always Modify-or-Create with the full desired property set (not just a
# create-if-missing check) -- idempotent AND self-correcting, since a stale or
# differently-configured pre-existing registration at this path must not be
# silently left in place.
#
# MatchRoles=":<db resource>" -- the LEADING COLON means "additionally grant
# this role for requests to THIS application only". It is what actually clears
# the 403: it gives the unauthenticated request just enough privilege to read
# the namespace's database and run PopHeat.API, scoped to this one application
# instead of granting UnknownUser a global role.
#
# Resource="" -- deliberately no extra resource gate. The dashboard/API is a
# public, read-only demo view by design (D-06, dashboard-api.spec R6: no
# login), so an additional custom application resource is redundant once
# MatchRoles supplies the required privilege.
# NOTE: the `iris session` terminal executes its input LINE BY LINE, so a
# brace block spread over several lines raises <SYNTAX> and every line inside
# it then runs unconditionally. Every conditional below is therefore kept on
# ONE physical line -- that is what makes re-running this script a true no-op
# (Modify on the existing app) instead of a no-op-with-errors.
iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF
set props("NameSpace") = "${IRIS_NAMESPACE}"
set props("Enabled") = 1
set props("DispatchClass") = "PopHeat.API"
set props("AutheEnabled") = 64
set props("Resource") = ""
set props("MatchRoles") = ":${DB_RESOURCE}"
if ##class(Security.Applications).Exists("/csp/popheat/api") { set sc = ##class(Security.Applications).Modify("/csp/popheat/api", .props) } else { set sc = ##class(Security.Applications).Create("/csp/popheat/api", .props) }
if 'sc { do \$System.Status.DisplayError(sc) }
halt
IRISEOF

echo "=== PopHeat: registering /csp/popheat static web application (dashboard.html, unauthenticated per D-06) ==="
# IRIS auto-creates a "/csp/popheat" web app for the namespace's own
# Interoperability Management Portal (Interop=1 in merge.cpf) -- Exists()
# alone would find that unrelated app and skip registration, leaving the
# portal (password-protected, no Path at all) in place instead of our
# dashboard. Modify-or-Create with the full desired property set corrects
# that in place: without an explicit Path the app points nowhere and every
# file under it 404s, whatever its auth settings say.
iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF
set props2("NameSpace") = "${IRIS_NAMESPACE}"
set props2("Enabled") = 1
set props2("Path") = "${APP_DIR}/iris/PopHeat/www/"
set props2("DispatchClass") = ""
set props2("AutheEnabled") = 64
set props2("Resource") = ""
set props2("MatchRoles") = ":${DB_RESOURCE}"
set props2("ServeFiles") = 1
if ##class(Security.Applications).Exists("/csp/popheat") { set sc = ##class(Security.Applications).Modify("/csp/popheat", .props2) } else { set sc = ##class(Security.Applications).Create("/csp/popheat", .props2) }
if 'sc { do \$System.Status.DisplayError(sc) }
halt
IRISEOF

echo "=== PopHeat: compiling PopHeat.Reading / PopHeat.BatchTelemetry / PopHeat.API ==="
iris session "$IRIS_INSTANCE" -U"$IRIS_NAMESPACE" <<IRISEOF
do ##class(%SYSTEM.OBJ).LoadDir("${APP_DIR}/iris/PopHeat","ck",,1)
halt
IRISEOF

echo "=== PopHeat: initializing IOP support classes in ${IRIS_NAMESPACE} ==="
cd "$APP_DIR"
iop --init

echo "=== PopHeat: migrating settings.py via iop ==="
iop --migrate settings.py

echo "=== PopHeat: enabling auto-start for PopHeat.Production (D-05) ==="
iris session "$IRIS_INSTANCE" -U"$IRIS_NAMESPACE" <<'IRISEOF'
do ##class(Ens.Director).SetAutoStart("PopHeat.Production")
halt
IRISEOF

echo "=== PopHeat: starting PopHeat.Production for this run ==="
iop --start PopHeat.Production --detach || echo "(already running -- ok on re-run)"

echo "=== PopHeat: status ==="
iop --status || true

echo "=== PopHeat: init complete ==="
