with open("src/main/AndroidManifest.xml", "r") as f:
    code = f.read()

code = code.replace("eu.kanade.tachiyomi.animeextension.all.webdav.WebDAV", "eu.kanade.tachiyomi.animeextension.all.webdav.WebDavFactory")

with open("src/main/AndroidManifest.xml", "w") as f:
    f.write(code)

print("Manifest Done")
