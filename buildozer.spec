[app]
title = Space Wars
package.name = spacewars
package.domain = org.amr

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

requirements = python3,pygame==2.6.1

orientation = portrait
fullscreen = 1

android.permissions = INTERNET

android.api = 31
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
