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
