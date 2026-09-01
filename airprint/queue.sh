#!/usr/bin/env bash
set -uo pipefail

QUEUE=$1
DEVICE=$2
LABEL=$3
LOCATION=$4
DRIVER=$5

lpadmin -p "${QUEUE}" \
	-v "${DEVICE}" \
	-m "${DRIVER}" \
	-D "${LABEL}" \
	-L "${LOCATION}" \
	-o printer-is-shared=true \
	-o printer-error-policy=retry-job \
	-E || exit 1

mkdir -p /var/cache/cups/images
cp /usr/share/airprint/printer.png "/var/cache/cups/images/${QUEUE}.png"
