[app]
title = Amazon River Disk
package.name = amazonriverdisk
package.domain = br.com.amazonriver
source.dir = .
source.include_exts = py,png
version = 1.0
requirements = python3,kivy==2.3.0,pyjnius
orientation = portrait
icon.filename = %(source.dir)s/icon.png
android.permissions = android.permission.READ_EXTERNAL_STORAGE,android.permission.WRITE_EXTERNAL_STORAGE,android.permission.MANAGE_EXTERNAL_STORAGE,android.permission.QUERY_ALL_PACKAGES
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
