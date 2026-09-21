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

echo "=== PopHeat: enabling Unauthenticated access on %Service_WebGateway (required for DASH-01/D-06 -- the per-app AutheEnabled=64 setting below is necessary but not sufficient; IRIS also gates unauthenticated CSP/REST access at the %Service_WebGateway system service, which ships Password-only by default) ==="
WG_AUTHE=$(iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF 2>&1 | grep -o 'WG_AUTHE=[0-9]*' | tail -1 | cut -d= -f2
set sc = ##class(Security.Services).Get("%Service_WebGateway", .props)
write "WG_AUTHE=",props("AutheEnabled"),!
halt
IRISEOF
)
# Bit 64 = Unauthenticated (Security.System AutheXxx constants). Add it to
# whatever is already enabled (e.g. 32 = Password) rather than overwrite, so
# an operator's existing auth methods for this service keep working.
if [ $((WG_AUTHE & 64)) -eq 0 ]; then
  NEW_WG_AUTHE=$((WG_AUTHE | 64))
  iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF
set svcProps("AutheEnabled") = ${NEW_WG_AUTHE}
set sc = ##class(Security.Services).Modify("%Service_WebGateway", .svcProps)
if 'sc { do \$System.Status.DisplayError(sc) }
halt
IRISEOF
fi

echo "=== PopHeat: creating PopHeat_Public resource/role for unauthenticated access (DASH-01/D-06) ==="
# UnknownUser (the identity unauthenticated requests map to) has zero roles by
# default -- without an explicit Use-permitted resource + role, AutheEnabled=64
# alone is not sufficient for the app to actually serve UnknownUser requests.
RES_EXISTS=$(iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF 2>&1 | grep -o 'RES_EXISTS=[01]' | tail -1 | cut -d= -f2
write "RES_EXISTS=",##class(Security.Resources).Exists("PopHeat_Public"),!
halt
IRISEOF
)
if [ "$RES_EXISTS" != "1" ]; then
  iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF
set sc = ##class(Security.Resources).Create("PopHeat_Public", "PopHeat public unauthenticated dashboard/API resource (D-06)", "", 0)
if 'sc { do \$System.Status.DisplayError(sc) }
halt
IRISEOF
fi
ROLE_EXISTS=$(iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF 2>&1 | grep -o 'ROLE_EXISTS=[01]' | tail -1 | cut -d= -f2
write "ROLE_EXISTS=",##class(Security.Roles).Exists("PopHeatPublic"),!
halt
IRISEOF
)
if [ "$ROLE_EXISTS" != "1" ]; then
  iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF
set sc = ##class(Security.Roles).Create("PopHeatPublic", "PopHeat public role, unauthenticated read-only access (D-06)", "PopHeat_Public:U", "")
if 'sc { do \$System.Status.DisplayError(sc) }
halt
IRISEOF
fi
UNKUSER_ROLES=$(iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF 2>&1 | grep -o 'UNKUSER_ROLES=.*' | tail -1 | cut -d= -f2
set sc = ##class(Security.Users).Get("UnknownUser", .uprops)
write "UNKUSER_ROLES=",uprops("Roles"),!
halt
IRISEOF
)
case ",${UNKUSER_ROLES}," in
  *,PopHeatPublic,*) ;;
  *)
    iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF
set roles = "PopHeatPublic"
set sc = ##class(Security.Users).AddRoles("UnknownUser", .roles)
if 'sc { do \$System.Status.DisplayError(sc) }
halt
IRISEOF
    ;;
esac

echo "=== PopHeat: registering /csp/popheat/api web application (PopHeat.API, unauthenticated per D-06) ==="
# Always Modify-or-Create with the full desired property set (not just a
# create-if-missing check) -- idempotent AND self-correcting, since a stale or
# differently-configured pre-existing registration at this path must not be
# silently left in place.
API_APP_EXISTS=$(iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF 2>&1 | grep -o 'API_APP_EXISTS=[01]' | tail -1 | cut -d= -f2
write "API_APP_EXISTS=",##class(Security.Applications).Exists("/csp/popheat/api"),!
halt
IRISEOF
)
iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF
set props("NameSpace") = "${IRIS_NAMESPACE}"
set props("Enabled") = 1
set props("DispatchClass") = "PopHeat.API"
set props("AutheEnabled") = 64
set props("Resource") = "PopHeat_Public"
if "${API_APP_EXISTS}" = "1" {
  set sc = ##class(Security.Applications).Modify("/csp/popheat/api", .props)
} else {
  set sc = ##class(Security.Applications).Create("/csp/popheat/api", .props)
}
if 'sc { do \$System.Status.DisplayError(sc) }
halt
IRISEOF

echo "=== PopHeat: registering /csp/popheat static web application (dashboard.csp, unauthenticated per D-06) ==="
# IRIS auto-creates a "/csp/popheat" web app for the namespace's own
# Interoperability Management Portal (Interop=1 in merge.cpf) -- Exists()
# alone would find that unrelated app and skip registration, leaving the
# portal (password-protected, wrong Path) in place instead of our dashboard.
# Modify-or-Create with the full desired property set corrects that in place.
DASH_APP_EXISTS=$(iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF 2>&1 | grep -o 'DASH_APP_EXISTS=[01]' | tail -1 | cut -d= -f2
write "DASH_APP_EXISTS=",##class(Security.Applications).Exists("/csp/popheat"),!
halt
IRISEOF
)
iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF
set props2("NameSpace") = "${IRIS_NAMESPACE}"
set props2("Enabled") = 1
set props2("Path") = "${APP_DIR}/iris/PopHeat/www"
set props2("DispatchClass") = ""
set props2("AutheEnabled") = 64
set props2("Resource") = "PopHeat_Public"
set props2("ServeFiles") = 1
if "${DASH_APP_EXISTS}" = "1" {
  set sc = ##class(Security.Applications).Modify("/csp/popheat", .props2)
} else {
  set sc = ##class(Security.Applications).Create("/csp/popheat", .props2)
}
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
