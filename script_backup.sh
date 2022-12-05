#!/bin/bash

BACKUP_DIR=/home/ubuntu/odoo_backups
ODOO_DATABASE=taz1
NOW=`date +"%Y-%m-%d_%H%M%S"`

sudo -u odoo pg_dump --file "$BACKUP_DIR/${ODOO_DATABASE}_$NOW.sql" $ODOO_DATABASE

# delete old backups
find ${BACKUP_DIR} -type f -mtime +30 -name "${ODOO_DATABASE}_*.sql" -delete
