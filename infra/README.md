# Infrastructure as code (S04)

Ansible describes both Raspberry Pis so a dead SD card or an OS rebuild is a repeatable procedure. It runs from the Mac over SSH.
Nothing here has been applied to a Pi. **Always start with `--check --diff` and read every line.**

| Group | Roles |
|---|---|
| both | `base`, `ssh_hardening`, `firewall`, `fail2ban`, `unattended_upgrades` |
| `app` | `docker`, `bajeti_app`, `backups`, `monitoring`, `github_runner` |
| `backup` | `storage`, `backup_target` |

Secrets: **Ansible Vault** (built in, free, nothing else to install). The vault password lives in the password manager. Real values stay out of git: `inventory/production.ini`, `group_vars/all/main.yml`, `group_vars/all/vault.yml` are git-ignored; only `*.example` files are committed.

## Set up (once, on the Mac)

```
cd infra/ansible
ansible-galaxy collection install -r requirements.yml
cp inventory/example.ini inventory/production.ini            # fill in the real hosts
cp group_vars/all/main.yml.example group_vars/all/main.yml   # fill in; the pinned versions are mandatory
cp group_vars/all/vault.yml.example group_vars/all/vault.yml
ansible-vault encrypt group_vars/all/vault.yml
```

Pins you must fill in: `docker_package_version` (list with `apt-cache madison docker-ce` on a Pi with Docker's repository), `cloudflared_version`, `age_version` and `age_sha256` (from the release page). The playbook stops if any is still a placeholder.

## Check mode first

```
ansible-playbook playbooks/site.yml --syntax-check
ansible-playbook playbooks/site.yml --check --diff --limit backup --ask-vault-pass
```

Check mode of the backup Pi changes nothing on it. Then the app Pi. A second run in check mode should report zero changes once a real run has converged.

## First real run (lock-out safety)

SSH hardening and the firewall refuse to change anything unless you pass `-e lockout_safe=true`. Before that: keep a second SSH session open, confirm key login works, then run. If a run hangs after an SSH or firewall change, the open session is how you undo it.

```
ansible-playbook playbooks/site.yml --diff --limit backup -e lockout_safe=true --ask-vault-pass
```

## Bootstrap a fresh Pi OS image (rebuild)

Follow `docs/runbooks/pi-os-upgrade.md`. In short: flash Raspberry Pi OS Lite 64-bit with SSH key only, reach it by its reserved address, restore the secrets bundle (the `bajeti_app` role stops until `.env` and the tunnel files exist), run the playbook, then `--tags start` to bring the stack up.

## GitHub runner

Registration is manual and the token is never stored here: GitHub, Settings, Actions, Runners, new self-hosted runner (Linux ARM64), run the commands it shows in `~/actions-runner`, install it as a service. TODO(S08): a dedicated unprivileged user.

## Add a role

Create `roles/<name>/{tasks,defaults,handlers,templates}`, prefix every variable with the role name, use fully qualified module names, add it to `playbooks/site.yml`, then run `yamllint -c .yamllint .` and `ansible-lint -c ../.ansible-lint playbooks/site.yml` from `infra/ansible`. CI runs the same.

## Rollback

Each role replaces one file or installs one package; the diff in check mode shows which. To undo a file, restore the previous version from the diff and run again. For a whole rebuild the rollback is the old-card image in `docs/runbooks/pi-os-upgrade.md` (step R).

## Not included on purpose

File sharing, the port-80 web server, the old tunnel tool, k3s and the other leftovers from the audit are not in the playbook.
