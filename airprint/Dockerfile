FROM debian:bookworm-slim AS splix-build
ENV DEBIAN_FRONTEND=noninteractive
# OpenPrinting SpliX 2.0.2, pinned to its release commit.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates git build-essential libcups2-dev libcupsimage2-dev libjbig-dev cups-ppdc \
 && git clone https://github.com/OpenPrinting/splix.git /src \
 && cd /src \
 && git checkout --detach 9bde257882a1ebcf15a97ff4685d34053383e3f8 \
 && sed -i \
      -e 's/pkg-config --cflags cups/cups-config --cflags/g' \
      -e 's/pkg-config --libs cups/cups-config --libs/g' \
      -e 's/pkg-config --variable=cups_serverbin cups/cups-config --serverbin/g' \
      -e 's/pkg-config --variable=cups_datadir cups/cups-config --datadir/g' \
      -e 's/-ljbig85/-ljbig/g' module.mk \
 && make -j2 DRV_ONLY=1 \
 && make -C ppd drv \
 && make install DRV_ONLY=1 DESTDIR=/out \
 && test -s /out/usr/lib/cups/filter/rastertoqpdl \
 && grep -q 'M2020 Series' /out/usr/share/cups/drv/splix-samsung.drv \
 && install -D -m 644 COPYING /out/usr/share/doc/splix-2.0.2/COPYING

FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      avahi-daemon \
      avahi-utils \
      ca-certificates \
      cups \
      cups-bsd \
      cups-client \
      cups-ppdc \
      cups-filters \
      curl \
      dbus \
      jq \
      python3 \
      snmp \
 && apt-get install -y --no-install-recommends \
      printer-driver-all \
      printer-driver-brlaser \
      printer-driver-cups-pdf \
      openprinting-ppds \
      foomatic-db-compressed-ppds \
 && apt-get install -y --no-install-recommends \
      libcupsimage2 \
      libgtk-3-0 \
      libjpeg62-turbo \
      libjbig0 \
      libgcrypt20 \
      lsb-release \
 && rm -rf /var/lib/apt/lists/*

COPY --from=splix-build /out/ /
# Generate the target PPD during the image build; fail if unavailable.
RUN mkdir -p /usr/share/cups/model \
 && ppdc -d /usr/share/cups/model /usr/share/cups/drv/splix-samsung.drv \
 && test -s /usr/share/cups/model/m2020.ppd

COPY cupsd.conf /etc/cups/cupsd.conf
COPY cupsd.conf /usr/share/airprint/cupsd.conf
COPY avahi-daemon.conf /etc/avahi/avahi-daemon.conf
COPY printer.png /usr/share/airprint/printer.png
COPY run.sh /run.sh
COPY monitor.sh /monitor.sh
COPY drivers.sh /drivers.sh
COPY discover.sh /discover.sh
COPY queue.sh /queue.sh
RUN chmod +x /run.sh /monitor.sh /drivers.sh /discover.sh /queue.sh

CMD ["/run.sh"]

COPY manual-driver.sh /manual-driver.sh
COPY ipp-probe.py /ipp-probe.py
RUN chmod +x /manual-driver.sh
