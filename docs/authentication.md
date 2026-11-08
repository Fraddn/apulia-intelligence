# Authentication

Every page and every data endpoint needs a login. Anyone can register.

## In short

- **Sign up:** username, email and password. No email is sent; the user is logged in right away.
- **Log in:** email *or* username, plus password. A value containing `@` is sent as `email`, anything else as `username`.
- **Staying logged in:** a server-side session. The browser holds only a cookie with a random session ID.
- **Log out:** the server deletes the session, so the cookie stops working at once.
- **Forgot password:** not available, because the app sends no email. Set a new password in the Django admin: `/admin/` → Users → the user → "change password".

## How it works

### Where the session lives

| Thing | Where | Who decides |
|---|---|---|
| Session ("this ID = user maria.rossi") | Server, SQLite table `django_session` | Server |
| Session cookie (`sessionid`) | Browser, `HttpOnly` so JavaScript cannot read it | Server creates and deletes it |
| CSRF cookie (`csrftoken`) | Browser, readable by JavaScript | Sent back as the `X-CSRFToken` header on changes |
| `user` in `frontend/src/session.ts` | Frontend memory | Nobody: a display copy only |

The frontend copy is used only to show the username and decide which page to render. Access is decided **only on the server**: every `/api/` request is checked against the session, whatever the frontend thinks.

### Passwords

Passwords are stored hashed: scrambled one way, never readable, not even by an admin. Django's validators reject passwords that are too short (under 8 characters), too common, entirely numeric or too similar to the username or email. allauth rate-limits repeated failed logins: 5 per username every 5 minutes and 10 per minute per IP. The Django admin login has the same limits (`apps/core/admin.py`). In production `ALLAUTH_TRUSTED_PROXY_COUNT=1` makes the per-IP limit count each visitor, not Caddy.

### Usernames

- At least 3 characters; letters, numbers, `.`, `-` and `_` only.
- No `@`, so a username can never be mistaken for an email at login.
- Stored lowercase and unique, so `Maria.Rossi` and `maria.rossi` are the same account.
- The header shows the username.

### What is public

| Path | Why |
|---|---|
| `/login`, `/signup`, `/account/verify-email/:token` | The account pages |
| `/api/health` | Version number in the header |
| `/api/summary` | Three totals on the login page (companies, funded projects, state-aid grants); nothing else |
| `/_allauth/browser/v1/...` | allauth's own endpoints (login, signup, session) |

Everything else under `/api/` answers **401** without a valid session. POST endpoints also need the CSRF token, or they answer **403**.

### Why sessions and not JWT

The frontend and API are served from the same domain by one server. In that setup cookie sessions are the simplest and safest choice, and the one allauth recommends for single-page apps:

- The cookie is `HttpOnly`, so a malicious script cannot read it (unlike tokens kept in `localStorage`).
- Logout and revocation take effect at once.
- There is no refresh-token logic to write.

JWT or allauth's `app` client (a token in a header) would make sense only for a mobile app or a separate API domain. API keys would suit other systems pulling data. Any of these can be added next to the sessions later.

### Language

The frontend sends `Accept-Language` (`it` or `en`) on every auth call. `LocaleMiddleware` uses it, so error messages come back in the user's language.

## Flows

### Opening a page while logged out

1. The router guard (`router.ts`) asks `session.ts` to load the session: `GET /_allauth/browser/v1/auth/session`. This also sets the `csrftoken` cookie.
2. The answer is 401 (nobody logged in), so the guard redirects to `/login?next=/the/page`.

### Logging in

1. `LoginView.vue` → `auth.login()` in `session.ts` → `POST /_allauth/browser/v1/auth/login` with `{username | email, password}`, plus the `X-CSRFToken` and `Accept-Language` headers.
2. allauth checks the password, creates the session and sets the `sessionid` cookie.
3. A 200 answer carries the user. `session.ts` stores it and the page goes to `next` (`safeNext` only accepts paths inside the app).
4. A 400 answer carries errors, which `authForm.ts` shows under the matching field. A 409 means already logged in and is treated as success. A 429 means too many attempts.

### Signing up

`SignupView.vue` → `POST /_allauth/browser/v1/auth/signup` with `{username, email, password}`. With verification off, the answer is 200 and the user is logged in.

### Loading data

Views call `api.ts`. The browser sends the cookies automatically, and `config/api.py` (`auth=django_auth`) checks the session. On a 401 (for example an expired session), `api.ts` calls the handler registered in `main.ts`, which clears the user and redirects to `/login?next=…`.

### Logging out

`UserMenu.vue` → `DELETE /_allauth/browser/v1/auth/session` with the CSRF header → the session is deleted → redirect to `/login`.

## Files

### Backend

| File | Role |
|---|---|
| `backend/config/settings.py` | allauth setup: `HEADLESS_ONLY`, `ACCOUNT_LOGIN_METHODS = {"email", "username"}`, `ACCOUNT_SIGNUP_FIELDS`, username rules, `ACCOUNT_EMAIL_VERIFICATION` (env, default `none`), `HEADLESS_FRONTEND_URLS`, session/CSRF/locale middleware, email settings |
| `backend/config/urls.py` | Mounts allauth at `/_allauth/` and blocks the password-reset endpoints (404) |
| `backend/config/api.py` | The lock: `NinjaAPI(auth=django_auth)` makes every `/api/` endpoint need a session |
| `backend/apps/core/accounts.py` | `username_validators` (allowed characters) |
| `backend/apps/core/api.py` | `/api/health`, public (`auth=None`) |
| `backend/apps/companies/api.py` | `/api/summary`, public (`auth=None`); all other endpoints need a login |
| `backend/apps/core/admin.py` | Applies the failed-login limits to the Django admin login |
| `backend/apps/core/tests.py` | `LoginRequiredTests`, `NoEmailTests`, `SignupFlowTests`, `SessionTests`, `LoginLimitTests` |

allauth (the library) does the actual work: password checks, hashing, sessions and rate limits.

### Frontend

| File | Role |
|---|---|
| `src/session.ts` | Holds the logged-in user (display copy); `loadSession`, `logout`, and `auth.login` / `auth.signup` / `auth.verifyEmail`; adds the CSRF and language headers |
| `src/router.ts` | Lists the routes (public ones have `meta.public`, login and signup also `guestOnly`); the guard redirects logged-out users to login and keeps logged-in users off login and signup; `safeNext`, `loginRoute` |
| `src/api.ts` | Data calls; `csrfToken()`, CSRF header on non-GET requests, `onUnauthorized` hook on 401 |
| `src/main.ts` | Registers the 401 handler (clear user, go to login); mounts the app after the first navigation, so the session is known before anything renders |
| `src/authForm.ts` | Shared form logic: busy state, field errors vs general errors, messages for 429 and offline |
| `src/views/LoginView.vue` | "Email or username" + password |
| `src/views/SignupView.vue` | Username, email, password, confirm password |
| `src/views/VerifyEmailView.vue` | Email confirmation link page; unused while verification is `none` |
| `src/components/AuthCard.vue` | Split-screen layout for account pages: brand panel with `/api/summary` totals, plus the form; one column on tablet and phone |
| `src/components/AuthNotice.vue` | Error, info and success message boxes |
| `src/components/UserMenu.vue` | Username and logout button in the header |
| `src/components/AppHeader.vue` | Hides the navigation when logged out |
| `src/App.vue` | Account pages render full-screen; other pages get the header and footer |
| `src/locales/it.ts`, `en.ts` | Texts under `auth` and `authBrand` |
| `src/__tests__/authGuard.spec.ts`, `AuthViews.spec.ts`, `UserMenu.spec.ts`, `api.spec.ts` | Tests |

### Config

| File | Role |
|---|---|
| `.env` / `.env.example` | `ACCOUNT_EMAIL_VERIFICATION`, email settings, `CORS_FRONTEND_URL` (base of the links in emails), `CSRF_TRUSTED_ORIGINS` |
| `frontend/vite.config.ts` | In development, proxies `/api` and `/_allauth` to Django, so cookies work on one origin. Production must route the same paths to Django on the same domain. |

## Turning email features on later

1. Set up an SMTP provider (for example Brevo or Mailjet, free tiers) and fill in the `EMAIL_*` settings in `.env`.
2. Set `ACCOUNT_EMAIL_VERIFICATION=mandatory`. Signup then answers 401 with a pending `verify_email` flow; `SignupView` shows "check your email", and the link opens `VerifyEmailView`.
3. Password reset needs both of these first:
   - remove the 404 block in `config/urls.py` and add the reset URLs back to `HEADLESS_FRONTEND_URLS`;
   - rebuild the request and new-password pages (they were removed on 2026-11-06).
