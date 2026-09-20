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

echo "=== PopHeat: installing iris-pex-embedded-python + tzdata ==="
pip3 install --quiet iris-pex-embedded-python tzdata

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

echo "=== PopHeat: compiling PopHeat.Reading / PopHeat.BatchTelemetry ==="
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
