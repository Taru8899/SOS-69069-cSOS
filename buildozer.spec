[app]
title = SOS 69069 cSOS
package.name = sos69069csos
package.domain = org.sos
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.include_patterns = assets/*,icon.png,presplash.png
version = 0.4

icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png
# Android splash background while loading (matches logo green)
android.presplash_color = #00C854

requirements = hostpython3==3.11.5,python3==3.11.5,kivy==2.3.0,requests,eth-account==0.10.0,eth-abi==4.2.1,eth-utils==2.3.1,eth-keys==0.4.0,eth-rlp==0.3.0,eth-typing==3.5.2,eth-hash==0.5.2,eth-keyfile==0.7.0,hexbytes==0.3.1,bitarray==2.8.1,rlp==3.0.0,pycryptodome==3.19.0,parsimonious==0.10.0,regex==2023.10.3,toolz==0.12.0,pyrsistent==0.19.3,attrs==23.1.0,cffi,pycparser,typing_extensions==4.9.0

orientation = portrait
android.permissions = INTERNET
android.api = 33
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True

[buildozer]
log_level = 2
