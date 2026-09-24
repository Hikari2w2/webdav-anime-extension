with open("src/main/java/eu/kanade/tachiyomi/animeextension/all/webdav/WebDAV.kt", "r") as f:
    code = f.read()

old_block = """            var displayNameText = prop.getElementsByTagNameNS("*", "displayname").item(0)?.textContent
            if (displayNameText.isNullOrEmpty()) {
                val decoded = try { URLDecoder.decode(href.trimEnd('/').substringAfterLast('/'), "UTF-8") } catch (e: Exception) { href.trimEnd('/').substringAfterLast('/') }
                displayNameText = decoded
            }
            val displayName = displayNameText"""

new_block = """            val displayNameText = prop.getElementsByTagNameNS("*", "displayname").item(0)?.textContent
            val displayName = if (displayNameText.isNullOrEmpty()) {
                try { URLDecoder.decode(href.trimEnd('/').substringAfterLast('/'), "UTF-8") } catch (e: Exception) { href.trimEnd('/').substringAfterLast('/') }
            } else {
                displayNameText
            }"""

code = code.replace(old_block, new_block)

with open("src/main/java/eu/kanade/tachiyomi/animeextension/all/webdav/WebDAV.kt", "w") as f:
    f.write(code)
