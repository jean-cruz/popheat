#!/usr/bin/env bash
# One-time (idempotent) setup for the PopHeat IRIS container:
# password, %Service_CallIn, POPHEAT namespace, ENSLIB read/write, the WSGI
# dashboard app + the namespace's Management Portal app, Business Rule compile,
# intersystems_pyprod + Flask install, production generate/load/start, SQL grants.
set -euo pipefail

CONTAINER=popheat-iris
IRIS_PASSWORD='PopHeat2026!'

echo "==> Waiting for IRIS to be healthy..."
until docker exec "$CONTAINER" iris list IRIS >/dev/null 2>&1; do sleep 2; done

echo "==> Step 1-7: security, namespace, web apps, business rules"
docker exec -i "$CONTAINER" iris session iris -U %SYS < "$(dirname "$0")/setup.txt"

echo "==> Step 8/9: installing intersystems_pyprod + flask"
docker exec "$CONTAINER" /usr/irissys/bin/irispython -m pip install --target /usr/irissys/mgr/python intersystems_pyprod flask -q

echo "==> Step 9/9: generating + loading the PyProd production"
docker exec "$CONTAINER" bash -c "
  export IRISINSTALLDIR=/usr/irissys
  export IRISUSERNAME=_SYSTEM
  export IRISPASSWORD='$IRIS_PASSWORD'
  export IRISNAMESPACE=POPHEAT
  export COMLIB=\$IRISINSTALLDIR/bin
  export PYTHONPATH=\$IRISINSTALLDIR/mgr/python:\$IRISINSTALLDIR/lib/python
  export LD_LIBRARY_PATH=\$IRISINSTALLDIR/bin
  /usr/irissys/mgr/python/bin/intersystems_pyprod /opt/popheat/src/python/popheat_production.py
"

echo "==> Granting the dashboard (unauthenticated) SQL read access + starting the production"
docker exec -i "$CONTAINER" iris session iris -U %SYS <<'EOF'
zn "POPHEAT"
set rs=##class(%SQL.Statement).%New() do rs.%Prepare("GRANT SELECT ON PopHeat.VenueReading TO UnknownUser")
set qr=rs.%Execute() write "grant VenueReading: ",qr.%SQLCODE,!
set rs2=##class(%SQL.Statement).%New() do rs2.%Prepare("GRANT SELECT ON PopHeat.BatchMetric TO UnknownUser")
set qr2=rs2.%Execute() write "grant BatchMetric: ",qr2.%SQLCODE,!
set sc=##class(Ens.Director).StartProduction("PopHeat.PopHeatProduction")
write "Start status: ",$system.Status.GetErrorText(sc),!
halt
EOF

echo "==> Done."
echo "    Dashboard:          http://localhost:52773/popheat/"
echo "    Management Portal:  http://localhost:52773/csp/popheat/UtilHome.csp  (_SYSTEM / $IRIS_PASSWORD)"
