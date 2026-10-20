# Bajeti Roadmap

Order: E0 → E1 → E2/E3 → E6 → E5 → E4 → E7 (E7 items can be picked up alongside any epic).
Tick items off as the matching PR merges.

## E0: Finish targets (issues #101, #103, #104, #105, #106)

- [ ] `schema/target.py` and `services/target_service.py`
- [ ] Targets routes (get, post, put, delete) in `routers/targets.py`
- [ ] Register targets router in `main.py`
- [ ] Enforce budget ownership in target service
- [ ] Real `downgrade()` for migration `9b38fdc94e38`
- [ ] `tests/test_targets.py`

## E1: Pi cleanup, security, performance (#110)

- [ ] Audit disk usage on the Pi (`docker system df`, `df -h`) and prune old images
- [ ] Log rotation in `docker-compose.yml`
- [ ] Trim the image: `.dockerignore` for `recover_backup/`, `Manrope.zip`, `allfileshas.txt`, `test.db`
- [ ] Verify scheduled DB backup to S3 and do a test restore (use SQLite `.backup`)
- [ ] Production container: no `--reload`, non-root user, port bound to `127.0.0.1`, pinned `cloudflared` tag
- [ ] Cookie flags (`secure`, `samesite=lax`), token lifetime, login rate limit
- [ ] Hash `users.security_answer`
- [ ] Fix allocation update/delete ownership check
- [ ] SQLite WAL mode, index on `expenses(user_id, month)`
- [ ] Remove N+1 spent-per-category query in `get_budget_overview`
- [ ] Point `API_BASE_URL` at localhost inside the container
- [ ] Pi OS: unattended upgrades, ufw, key-only ssh, fail2ban, check SD card wear

## E2: Analytics page (#111)

- [ ] Monthly totals endpoint (spend only, excludes withdrawals)
- [ ] Category breakdown for a month endpoint
- [ ] Replace the "Under Construction" `analytics.html`
- [ ] ECharts drill-down: month → category → expense list

## E3: Recurring expenses (#112)

- [ ] `RecurringExpense` model and migration
- [ ] CRUD at `/api/recurring`
- [ ] `GET /due` and `POST /{id}/approve` (creates an expense)
- [ ] "Due" strip on the dashboard with one-tap approve

## E4: Payment capture, M-Pesa and email (#113)

- [ ] `PendingPayment` model and migration
- [ ] Parser service for M-Pesa SMS and payment emails, with tests
- [ ] `POST /api/pending-payments` (token protected)
- [ ] "Paste message" box and category-request inbox on the dashboard
- [ ] Ingestion transport: see `docs/backlog.md`

## E5: Progressive web app (#114)

- [ ] UI brief: palette tokens, 4px spacing, `em` usage, template structure, screenshots
- [ ] Prototype in Claude web and review
- [ ] Manifest, icons, iOS meta tags, safe-area insets
- [ ] Service worker (static cache, offline shell, never cache authenticated responses)
- [ ] Install prompt

## E6: Future planning (#115)

- [ ] Plan/goal model with 1, 5 and 10 year horizons
- [ ] Progress view (saved to date vs goal, monthly amount needed)
- [ ] Restructure scenarios (recession, retrenchment, raise) compared with the live budget

## E7: Code and workflow improvements (#116)

- [ ] Pydantic v2 `from_attributes`; Decimal for money in schemas
- [ ] CI on Python 3.11 plus lint and coverage
- [ ] Tests for budgets, allocations, transfers, withdrawals
- [ ] Remove old `app/requests.py` and dead code
- [ ] Shared handler error handling
- [ ] Pre-merge migration check against a copy of the production DB
- [ ] Run `alembic upgrade head` in the container start script
