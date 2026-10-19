# Ansible (drafts from S02, extended in S04)

Nothing here has been applied to a Pi. Run with `--check --diff` first and read the output.

- `roles/storage`: creates the backups folder on the backup Pi's existing mount. It never formats or partitions.
- `roles/backup_target`: the pull script, `pull.env`, the systemd unit and timer on the backup Pi.
- `roles/backups`: on the app Pi, the outgoing folder and the restricted pull key (`rrsync -ro`).

Variables (set in the git-ignored inventory or `group_vars`, not in the repo): `backup_dir`, `app_pi_user`,
`pull_public_key`, `pull_ping_url` (secret, vault it), `age_recipient` (public key).
