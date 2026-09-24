with open("src/main/java/eu/kanade/tachiyomi/animeextension/all/webdav/WebDAV.kt", "r") as f:
    code = f.read()

old_block = """            if (isRoot) {
                // Only keep files directly in the root folder
                videoFiles = videoFiles.filter {
                    val fileDir = it.href.trimEnd('/').substringBeforeLast('/')
                    fileDir == rootUrlNoSlash
                }
            }"""

new_block = """            if (isRoot) {
                // Only keep files directly in the root folder
                videoFiles = videoFiles.filter {
                    val fileDir = it.href.trimEnd('/').substringBeforeLast('/')
                    fileDir == rootUrlNoSlash || fileDir == folderUrl.trimEnd('/')
                }
            }"""

code = code.replace(old_block, new_block)

with open("src/main/java/eu/kanade/tachiyomi/animeextension/all/webdav/WebDAV.kt", "w") as f:
    f.write(code)

print("isRoot fix done")
