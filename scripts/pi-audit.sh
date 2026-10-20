#!/usr/bin/env bash
# pi-audit.sh: strictly read-only audit of a Raspberry Pi.
#
# Usage:  ./pi-audit.sh app      (the Pi that runs Bajeti)
#         ./pi-audit.sh backup   (the Pi with the backup SSD)
#
# It changes nothing: no package, service or config changes, and the only file
# it writes is ./pi-audit-report.txt (git-ignored). Everything is redacted
# before it is written, but you MUST still read the report before sharing it.
#
# Commands that need root are tried with `sudo -n` (no password prompt). If sudo
# is not available the section says so and the audit carries on.

set -u
export LC_ALL=C
# sshd, nft, iptables, ufw and smartctl live in /usr/sbin, which a normal user's PATH lacks.
export PATH="$PATH:/usr/sbin:/sbin"

ROLE="${1:-}"
case "$ROLE" in
  app|backup) ;;
  *) echo "usage: $0 app|backup" >&2; exit 2 ;;
esac

# Set PI_AUDIT_REPORT=/dev/stdout to stream the report instead of writing a file
# (useful when running it over ssh with `bash -s`, so nothing is left on the Pi).
REPORT="${PI_AUDIT_REPORT:-./pi-audit-report.txt}"
HOST_SHORT="$(hostname 2>/dev/null || true)"
HOST_FQDN="$(hostname -f 2>/dev/null || true)"

SUDO=""
if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
  SUDO="sudo -n"
fi

have() { command -v "$1" >/dev/null 2>&1; }

section() { printf '\n==== %s ====\n' "$1"; }

# run <command...>: print the command, then its output (stdout and stderr).
run() {
  printf '$ %s\n' "$*"
  "$@" 2>&1 || true
}

# runs <shell string>: same, for pipelines.
runs() {
  printf '$ %s\n' "$1"
  bash -c "$1" 2>&1 || true
}

# Docker may need sudo.
DOCKER=""
if have docker; then
  if docker info >/dev/null 2>&1; then
    DOCKER="docker"
  elif [ -n "$SUDO" ] && $SUDO docker info >/dev/null 2>&1; then
    DOCKER="$SUDO docker"
  fi
fi

audit() {
  echo "Bajeti Pi audit report. Role: $ROLE"
  echo "Generated: $(date -u +%Y-%m-%dT%H:%MZ)"
  echo "NOTE: this report has been redacted automatically (IPs, MACs, hostname,"
  echo "home usernames, secret-looking lines, long tokens). It must still be"
  echo "reviewed by the owner before it is shared. Do not commit it."
  echo "Sudo available without a password: $([ -n "$SUDO" ] && echo yes || echo no)"
  echo "Docker accessible: $([ -n "$DOCKER" ] && echo yes || echo no)"

  section "OS and hardware"
  runs "grep -E '^(PRETTY_NAME|VERSION_CODENAME|VERSION_ID)=' /etc/os-release"
  run uname -srmv
  runs "tr -d '\\0' < /proc/device-tree/model; echo"
  runs "cat /etc/rpi-issue 2>/dev/null | head -5"
  if have rpi-eeprom-update; then run rpi-eeprom-update; else echo "rpi-eeprom-update not installed"; fi
  runs "findmnt -no SOURCE,FSTYPE /"
  runs "findmnt -no SOURCE,FSTYPE /boot /boot/firmware 2>/dev/null"

  section "Support status and packages"
  runs "grep -h -E '^(deb|URIs:|Suites:)' /etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null"
  # Do sources still resolve? Read-only HEAD requests, nothing is written.
  codename="$(. /etc/os-release 2>/dev/null; echo "${VERSION_CODENAME:-}")"
  if have curl && [ -n "$codename" ]; then
    for url in $(grep -h -E '^deb ' /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null \
                   | grep -o -E 'https?://[^ ]+' | sort -u); do
      code="$(curl -s -o /dev/null -m 8 -w '%{http_code}' "${url%/}/dists/$codename/Release" 2>/dev/null)"
      echo "source ${url} -> dists/${codename}/Release HTTP ${code:-none}"
    done
  fi
  runs "apt list --upgradable 2>/dev/null | tail -n +2 | wc -l"
  runs "apt-mark showhold"
  runs "apt-mark showmanual | tr '\\n' ' '; echo"
  runs "dpkg-query -W -f='\${Package} \${Version}\\n' openssh-server docker-ce docker-compose-plugin containerd.io python3 sqlite3 2>/dev/null"
  runs "ls /var/run/reboot-required 2>/dev/null && echo 'reboot required'"
  runs "systemctl is-active unattended-upgrades fail2ban ufw 2>/dev/null"

  section "Services and schedules"
  runs "systemctl list-unit-files --state=enabled --no-pager --no-legend | awk '{print \$1}'"
  runs "systemctl --failed --no-pager --no-legend"
  runs "systemctl list-timers --all --no-pager"
  runs "ls /etc/cron.d /etc/cron.hourly /etc/cron.daily /etc/cron.weekly /etc/cron.monthly 2>/dev/null"
  if [ -n "$SUDO" ]; then
    for f in $($SUDO ls /var/spool/cron/crontabs 2>/dev/null); do
      echo "--- crontab for user: $f"
      $SUDO cat "/var/spool/cron/crontabs/$f" 2>&1 | grep -v -E '^\s*(#|$)' || true
    done
  else
    runs "crontab -l 2>&1 | grep -v -E '^\\s*(#|\$)'"
  fi

  section "Network exposure"
  runs "${SUDO:+$SUDO }ss -tulpn"
  if have ufw; then runs "${SUDO:+$SUDO }ufw status verbose"; else echo "ufw not installed"; fi
  if have nft; then runs "${SUDO:+$SUDO }nft list ruleset | head -80"; fi
  if have iptables; then runs "${SUDO:+$SUDO }iptables -S | head -60"; fi
  if [ -n "$SUDO" ] && have sshd; then
    runs "$SUDO sshd -T | grep -E '^(permitrootlogin|passwordauthentication|pubkeyauthentication|allowusers|port) '"
  else
    runs "grep -h -i -E '^\\s*(PermitRootLogin|PasswordAuthentication|PubkeyAuthentication|AllowUsers|Port)\\b' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/* 2>/dev/null"
  fi

  section "Accounts"
  runs "getent group sudo adm docker | cut -d: -f1,4"
  runs "${SUDO:+$SUDO }grep -r -h 'NOPASSWD' /etc/sudoers /etc/sudoers.d 2>/dev/null | sed 's/#.*//' | grep -v '^\\s*\$'"
  # Count only. The contents of authorized_keys are never printed.
  for home in /home/* /root; do
    [ -d "$home" ] || continue
    n="$($SUDO grep -c -v -E '^\s*(#|$)' "$home/.ssh/authorized_keys" 2>/dev/null || echo 0)"
    echo "authorized_keys entries for $home: $n"
  done
  runs "last -n 10 -w | head -12"
  runs "awk -F: '\$7 !~ /(nologin|false)\$/ {print \$1, \$7}' /etc/passwd"

  section "Docker"
  if [ -n "$DOCKER" ]; then
    runs "$DOCKER version --format 'engine {{.Server.Version}}'"
    runs "$DOCKER compose version"
    runs "$DOCKER ps -a --format '{{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'"
    # Never `docker inspect` whole objects: they contain environment values.
    runs "$DOCKER ps -aq | xargs -r $DOCKER inspect -f '{{.Name}} user={{.Config.User}} restart={{.HostConfig.RestartPolicy.Name}} privileged={{.HostConfig.Privileged}} readonly_rootfs={{.HostConfig.ReadonlyRootfs}} network={{.HostConfig.NetworkMode}} compose_dir={{index .Config.Labels \"com.docker.compose.project.working_dir\"}}'"
    runs "$DOCKER images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}'"
    runs "$DOCKER volume ls"
    runs "$DOCKER network ls"
    runs "$DOCKER system df"
    runs "${SUDO:+$SUDO }cat /etc/docker/daemon.json 2>/dev/null"
  else
    echo "docker not available or not accessible"
  fi

  section "Storage"
  runs "lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT"
  runs "findmnt -t ext4,vfat,xfs,btrfs,exfat,ntfs,nfs,cifs -o TARGET,SOURCE,FSTYPE,OPTIONS"
  runs "grep -v -E '^\\s*#' /etc/fstab"
  run df -h
  if have smartctl && [ -n "$SUDO" ]; then
    for d in $(lsblk -dno NAME,TYPE | awk '$2=="disk" && $1 !~ /^mmcblk/ {print "/dev/"$1}'); do
      runs "$SUDO smartctl -H $d"
    done
  else
    echo "smartctl not available (or no sudo): SMART not checked"
  fi
  runs "${SUDO:+$SUDO }du -xh --max-depth=1 /var/log 2>/dev/null | sort -rh | head -10"
  runs "${SUDO:+$SUDO }du -xh --max-depth=1 /var/lib/docker 2>/dev/null | sort -rh | head -10"
  runs "journalctl --disk-usage"

  section "Health"
  if have vcgencmd; then
    run vcgencmd get_throttled
    run vcgencmd measure_temp
  fi
  run free -h
  run uptime
  runs "${SUDO:+$SUDO }dmesg 2>/dev/null | grep -i -E 'mmc|under-?voltage|voltage|usb.*(error|reset)|i/o error|ext4-fs error' | tail -20"

  section "GitHub Actions runner"
  runs "systemctl list-units --all --no-pager --no-legend 'actions.runner.*' | awk '{print \$1, \$3, \$4}'"
  for unit in $(systemctl list-units --all --no-pager --no-legend 'actions.runner.*' 2>/dev/null | awk '{print $1}'); do
    runs "systemctl show $unit -p User -p WorkingDirectory -p ExecStart --no-pager | cut -c1-200"
    wd="$(systemctl show "$unit" -p WorkingDirectory --value 2>/dev/null)"
    # Version only. Runner credential files are never read.
    [ -x "$wd/bin/Runner.Listener" ] && runs "'$wd/bin/Runner.Listener' --version"
  done

  section "Backups"
  runs "${SUDO:+$SUDO }grep -r -l -i -E 'backup|rsync|restic|borg' /etc/cron.d /var/spool/cron/crontabs 2>/dev/null"
  for dir in /home/*/backups /home/*/backups/* /mnt/* /media/*/* ; do
    [ -d "$dir" ] || continue
    echo "--- files from the last 14 days under $dir (date, bytes, name)"
    find "$dir" -maxdepth 2 -type f -mtime -14 -printf '%TY-%Tm-%Td %s %f\n' 2>/dev/null | sort | tail -30
  done

  if [ "$ROLE" = "backup" ]; then
    section "Backup Pi extras: what it runs and what is on the SSD"
    runs "systemctl list-units --type=service --state=running --no-pager --no-legend | awk '{print \$1}'"
    # Directory names and sizes only. File contents are never read.
    for mp in $(findmnt -rno TARGET -t ext4,xfs,btrfs,exfat,ntfs | grep -v -E '^(/|/boot.*)$'); do
      echo "--- top level of $mp (names and sizes only)"
      ${SUDO:+$SUDO }du -xh --max-depth=1 "$mp" 2>/dev/null | sort -rh | head -25
      runs "findmnt -no OPTIONS,FSTYPE,SOURCE '$mp'"
    done
    runs "lsblk -o NAME,SIZE,MODEL,TRAN,FSTYPE,LABEL"
  fi

  echo
  echo "==== end of report ===="
}

# Redaction. Applied to everything before it reaches the report file.
# Order matters: MAC addresses first, then IPv6, then IPv4.
redact() {
  perl -pe '
    BEGIN {
      $h1 = $ENV{AUDIT_HOST_SHORT}; $h2 = $ENV{AUDIT_HOST_FQDN};
    }
    # Lines that look like they contain a secret are dropped entirely: an AWS key id, a
    # private key header, or a secret-like name followed by "=" or ":" and a value.
    # Plain words such as "PasswordAuthentication no" or "NOPASSWD" are kept.
    if (/AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE|(secret|token|passw(or)?d|api[_-]?key|private[_-]?key|credential)\w*\s*[=:]\s*\S{6,}/i) {
      $_ = "<REDACTED LINE: looked like a secret>\n"; next;
    }
    s/\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b/<MAC>/g;
    s/\b(?:[0-9A-Fa-f]{1,4}:){3,7}[0-9A-Fa-f]{0,4}\b/<IPV6>/g;
    s/(?<![0-9A-Fa-f])[0-9A-Fa-f]{0,4}::[0-9A-Fa-f:]*/<IPV6>/g;
    s/\b(?:\d{1,3}\.){3}\d{1,3}(?:\/\d{1,2})?\b/<IPV4>/g;
    s/\Q$h2\E/<HOST>/g if length $h2;
    s/\Q$h1\E/<HOST>/g if length $h1;
    s#/home/[^/\s]+#/home/<USER>#g;
    s/\b[A-Za-z0-9+\/_=-]{40,}\b/<LONGSTRING>/g;
  '
}

export AUDIT_HOST_SHORT="$HOST_SHORT" AUDIT_HOST_FQDN="$HOST_FQDN"
audit 2>&1 | redact > "$REPORT"
echo "Wrote $REPORT. Read it and remove anything sensitive before sharing. Do not commit it." >&2
