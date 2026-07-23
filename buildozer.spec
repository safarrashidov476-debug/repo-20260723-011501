[app]
title = Ovozli Labirint
package.name = ovozlilabirint
package.domain = org.uzblind

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json

version = 1.0
requirements = python3,kivy,plyer,pyjnius

orientation = portrait
fullscreen = 1

# Ko'zi ojiz foydalanuvchilar TalkBack bilan ishlatishi mumkin bo'lishi uchun
android.allow_backup = True
android.permissions = INTERNET,ACCESS_NETWORK_STATE

android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
