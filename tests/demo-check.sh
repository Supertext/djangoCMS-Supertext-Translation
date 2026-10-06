#!/usr/bin/env bash
# CI: starts the demo image twice against PostgreSQL with the stand-in API, checks the demo
# accounts (created once, never duplicated, passwords never logged) and translates the sample
# article. Needs: docker image supertext-djangocms-demo, PostgreSQL at $PG_URL, the stand-in on 127.0.0.1:8765.
set -euo pipefail
PORT=8000
B=http://127.0.0.1:$PORT
export DEMO_ADMIN_EMAIL=ci-admin@example.com DEMO_ADMIN_PASSWORD="ci-$(openssl rand -hex 8)"
export DEMO_EDITOR_EMAIL=ci-editor@example.com DEMO_EDITOR_PASSWORD="ci-$(openssl rand -hex 8)"
py() { docker exec -e SUPERTEXT_API_KEY=anything -e SUPERTEXT_API_URL=http://127.0.0.1:8765/v1/ -w /app/demo demo python manage.py "$@"; }

start() {
	docker rm -f demo >/dev/null 2>&1 || true
	docker run -d --name demo --network host -e PORT=$PORT -e DATABASE_URL="$PG_URL" -e DJANGO_SECRET_KEY=ci \
		-e DEMO_ADMIN_EMAIL -e DEMO_ADMIN_PASSWORD -e DEMO_EDITOR_EMAIL -e DEMO_EDITOR_PASSWORD \
		-e SUPERTEXT_API_KEY=anything -e SUPERTEXT_API_URL=http://127.0.0.1:8765/v1/ supertext-djangocms-demo >/dev/null
	for _ in $(seq 90); do curl -sf -o /dev/null $B/en/admin/login/ && break; sleep 2; done
	curl -sf -o /dev/null $B/en/admin/login/
	docker logs demo 2>&1 | grep '\[demo\]' || true
}

start
start   # second start: nothing duplicated or changed
docker logs demo 2>&1 | grep > /dev/null 'DEMO_EDITOR: account exists, left unchanged'
logs=$(docker logs demo 2>&1)
if grep -qF -e "$DEMO_ADMIN_PASSWORD" -e "$DEMO_EDITOR_PASSWORD" <<< "$logs"; then echo "A password appeared in the log"; exit 1; fi

py shell -c "
from django.contrib.auth.models import User
users = {u.email: u for u in User.objects.all()}
assert sorted(users) == ['ci-admin@example.com', 'ci-editor@example.com'], sorted(users)
assert users['ci-admin@example.com'].is_superuser
editor = users['ci-editor@example.com']
assert not editor.is_superuser and editor.has_perm('djangocms_supertext.translate') and editor.has_perm('djangocms_text.change_text')
print('accounts OK')"

py supertext_check
PAGE=$(py shell -c "from cms.models import PageContent; print(PageContent.admin_manager.get(language='en', title='Swiss chocolate, shipped worldwide').page_id)" | tail -1)
py supertext_translate "$PAGE" --from en | tee /tmp/translate.log
test "$(grep -c ': translated' /tmp/translate.log)" = 3
py supertext_translate "$PAGE" --from en --to de-ch | grep > /dev/null 'skipped'

page=$(curl -sf "$B/de-ch/schweizer-schokolade-weltweit-versandt/")
echo "$page" | grep > /dev/null 'Schweizer Schokolade, weltweit versandt'
echo "$page" | grep > /dev/null '<strong>Berner</strong>'
echo "$page" | grep > /dev/null 'href="https://www.supertext.com"'
curl -sf "$B/fr-ch/chocolat-suisse-expedie-dans-le-monde-entier/" | grep > /dev/null 'De Berne vers le monde'
echo "Demo check passed"
