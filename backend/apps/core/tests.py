import subprocess
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from apps.core.version import resolve_version


class HealthTests(TestCase):
    @override_settings(APP_VERSION="2026.11.4")
    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "version": "2026.11.4"})


class ResolveVersionTests(SimpleTestCase):
    def test_env_value_wins(self):
        with mock.patch("apps.core.version.subprocess.run") as run:
            self.assertEqual(resolve_version("2026.11.5"), "2026.11.5")
        run.assert_not_called()

    def test_env_value_leading_v_is_stripped(self):
        self.assertEqual(resolve_version("v2026.11.5"), "2026.11.5")

    def test_falls_back_to_latest_git_tag(self):
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout="v2026.11.4\n")
        with mock.patch("apps.core.version.subprocess.run", return_value=result):
            self.assertEqual(resolve_version(""), "2026.11.4")

    def test_dev_when_git_unavailable(self):
        for error in (FileNotFoundError(), subprocess.TimeoutExpired("git", 2)):
            with self.subTest(error=type(error).__name__):
                with mock.patch("apps.core.version.subprocess.run", side_effect=error):
                    self.assertEqual(resolve_version(""), "dev")

    def test_dev_when_no_tags(self):
        result = subprocess.CompletedProcess(args=[], returncode=128, stdout="")
        with mock.patch("apps.core.version.subprocess.run", return_value=result):
            self.assertEqual(resolve_version(""), "dev")


class SessionTests(TestCase):
    url = "/_allauth/browser/v1/auth/session"

    def test_anonymous(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()["meta"]["is_authenticated"])

    def test_logged_in_user_is_returned(self):
        user = get_user_model().objects.create_user("mario", "mario@example.com", "pw")
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["user"]["email"], "mario@example.com")
        self.assertIn("display", response.json()["data"]["user"])

    def test_redirects_after_login_and_logout_go_to_the_app(self):
        from django.conf import settings

        self.assertEqual(settings.LOGIN_REDIRECT_URL, "/")
        self.assertEqual(settings.ACCOUNT_LOGOUT_REDIRECT_URL, "/")


class LoginRequiredTests(TestCase):
    def test_api_rejects_anonymous_requests(self):
        for url in ["/api/stats", "/api/companies", "/api/companies/03132170717"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 401)

    def test_discover_rejects_anonymous_requests(self):
        self.assertEqual(self.client.post("/api/companies/03132170717/discover").status_code, 401)

    def test_health_stays_public(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)

    def test_summary_is_public_and_only_has_totals(self):
        response = self.client.get("/api/summary")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"companies": 0, "funded_projects": 0, "aid_grants": 0})

    def test_logged_in_user_can_read_the_api(self):
        self.client.force_login(get_user_model().objects.create_user("mario", "mario@example.com", "pw"))
        self.assertEqual(self.client.get("/api/companies").status_code, 200)

    def test_discover_requires_csrf_token(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        client.force_login(get_user_model().objects.create_user("mario", "mario@example.com", "pw"))
        self.assertEqual(client.post("/api/companies/03132170717/discover").status_code, 403)


class NoEmailTests(TestCase):
    base = "/_allauth/browser/v1/auth"

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def test_signup_logs_in_straight_away_without_email(self):
        from django.core import mail

        response = self.client.post(f"{self.base}/signup", {
            "email": "nuovo@example.com", "username": "nuovo", "password": "Puglia-2026-sicura",
        }, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(self.client.get("/api/companies").status_code, 200)

    def test_password_reset_is_disabled(self):
        from django.core import mail

        get_user_model().objects.create_user("mario", "mario@example.com", "pw")
        for path, body in [("/password/request", {"email": "mario@example.com"}), ("/password/reset", {"key": "x", "password": "y"})]:
            with self.subTest(path=path):
                response = self.client.post(f"{self.base}{path}", body, content_type="application/json")
                self.assertEqual(response.status_code, 404)
        self.assertEqual(len(mail.outbox), 0)


@override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
class SignupFlowTests(TestCase):
    base = "/_allauth/browser/v1/auth"

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def post(self, path, data):
        return self.client.post(f"{self.base}{path}", data, content_type="application/json")

    def signup(self):
        return self.post("/signup", {
            "email": "nuovo@example.com", "username": "Maria.Rossi", "password": "Puglia-2026-sicura",
        })

    def test_signup_shows_the_username(self):
        from allauth.account.models import EmailAddress

        self.signup()
        EmailAddress.objects.filter(email="nuovo@example.com").update(verified=True)
        self.post("/login", {"username": "maria.rossi", "password": "Puglia-2026-sicura"})
        self.assertEqual(self.client.get(f"{self.base}/session").json()["data"]["user"]["display"], "maria.rossi")

    def test_signup_needs_only_username_email_and_password(self):
        response = self.post("/signup", {"email": "x@example.com", "password": "Puglia-2026-sicura"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual({e["param"] for e in response.json()["errors"]}, {"username"})

    def verified_user(self):
        from allauth.account.models import EmailAddress

        self.signup()
        EmailAddress.objects.filter(email="nuovo@example.com").update(verified=True)
        self.client.logout()

    def test_username_is_stored_lowercase(self):
        self.signup()
        self.assertEqual(get_user_model().objects.get(email="nuovo@example.com").username, "maria.rossi")

    def test_login_with_username_in_any_case(self):
        self.verified_user()
        response = self.post("/login", {"username": "MARIA.rossi", "password": "Puglia-2026-sicura"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/companies").status_code, 200)

    def test_login_with_email_still_works(self):
        self.verified_user()
        response = self.post("/login", {"email": "nuovo@example.com", "password": "Puglia-2026-sicura"})
        self.assertEqual(response.status_code, 200)

    def test_username_rules(self):
        for username, code in [("ab", "min_length"), ("maria@rossi", "invalid_username"), ("maria rossi", "invalid_username")]:
            with self.subTest(username=username):
                response = self.post("/signup", {
                    "email": "y@example.com", "username": username, "password": "Puglia-2026-sicura",
                })
                self.assertEqual(response.status_code, 400)
                self.assertIn(code, {e["code"] for e in response.json()["errors"] if e.get("param") == "username"})

    def test_username_must_be_unique(self):
        self.signup()
        response = self.post("/signup", {
            "email": "altro@example.com", "username": "maria.rossi", "password": "Puglia-2026-sicura",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", {e.get("param") for e in response.json()["errors"]})

    def test_signup_requires_email_verification(self):
        from django.core import mail

        response = self.signup()
        self.assertEqual(response.status_code, 401)
        flows = {flow["id"]: flow for flow in response.json()["data"]["flows"]}
        self.assertTrue(flows["verify_email"]["is_pending"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/account/verify-email/", mail.outbox[0].body)
        self.assertEqual(self.client.get("/api/companies").status_code, 401)

    def test_verified_user_is_logged_in_and_can_use_the_api(self):
        from allauth.account.models import EmailAddress

        self.signup()
        EmailAddress.objects.filter(email="nuovo@example.com").update(verified=True)
        self.client.logout()
        response = self.post("/login", {"email": "nuovo@example.com", "password": "Puglia-2026-sicura"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/companies").status_code, 200)

    def test_wrong_password_is_rejected(self):
        response = self.post("/login", {"email": "nobody@example.com", "password": "wrong-password"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/api/companies").status_code, 401)

    def test_errors_follow_the_requested_language(self):
        response = self.client.post(
            f"{self.base}/signup", {"email": "x@example.com", "password": "123"},
            content_type="application/json", HTTP_ACCEPT_LANGUAGE="it",
        )
        self.assertEqual(response.status_code, 400)
        messages = " ".join(error["message"] for error in response.json()["errors"])
        self.assertIn("Questa password è interamente numerica", messages)


class LoginLimitTests(TestCase):
    login = "/_allauth/browser/v1/auth/login"

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def fail_login(self, ip, username):
        return self.client.post(
            self.login, {"username": username, "password": "wrong-password"},
            content_type="application/json", HTTP_X_FORWARDED_FOR=ip,
        )

    @override_settings(ALLAUTH_TRUSTED_PROXY_COUNT=1)
    def test_limits_count_each_visitor_behind_the_proxy(self):
        for n in range(10):
            self.fail_login("203.0.113.1", f"user{n}")
        self.assertIn("too_many_login_attempts", self.fail_login("203.0.113.1", "other").content.decode())
        self.assertNotIn("too_many_login_attempts", self.fail_login("203.0.113.2", "other").content.decode())

    def test_admin_login_is_rate_limited(self):
        get_user_model().objects.create_superuser("boss", "boss@example.com", "Puglia-2026-sicura")
        for _ in range(5):
            response = self.client.post("/admin/login/", {"username": "boss", "password": "wrong"})
            self.assertEqual(response.status_code, 200)
        response = self.client.post("/admin/login/", {"username": "boss", "password": "Puglia-2026-sicura"})
        self.assertEqual(response.status_code, 429)
