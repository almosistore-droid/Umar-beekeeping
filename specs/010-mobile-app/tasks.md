# Tasks: 010-mobile-app
- [x] T1 Constitution II: list the login endpoints that verify by their own means (bot-confirmed one-time code, device token)
- [x] T2 Backend: models LoginCode, DeviceSession + migration 0009; device_auth_service; endpoints; X-Bot-Auth; tests; i18n
- [x] T3 Bot: /start login_<code> → confirm/cancel buttons → backend; WEBAPP_URL_FILE (dev tunnel); dev compose bot service
- [x] T4 Frontend: manifest, icons, sw.js, iOS meta; useAuth device session; login screen with polling; install hint; logout
- [x] T5 Frontend: CameraScanner (BarcodeDetector / jsQR) on «Сканер» outside Telegram
- [x] T6 nginx: rate limits for login endpoints, Permissions-Policy camera=(self)
- [x] T7 Tests, screenshots, docs (README, TESTING, CLAUDE.md)
