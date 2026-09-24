import re

with open("src/main/java/eu/kanade/tachiyomi/animeextension/all/webdav/WebDAV.kt", "r") as f:
    code = f.read()

# Add SimpleDateFormat and Locale imports
if "java.text.SimpleDateFormat" not in code:
    code = code.replace("import java.io.ByteArrayInputStream", "import java.text.SimpleDateFormat\nimport java.util.Locale\nimport java.net.URLDecoder\nimport java.io.ByteArrayInputStream")

# Fix trailing slash for anime folder URL
old_folder_url = """val folderUrl = if (file.href.startsWith("http")) file.href else serverUrl.replace(Regex("(https?://[^/]+).*"), "$1") + file.href"""
new_folder_url = """var folderUrl = if (file.href.startsWith("http")) file.href else serverUrl.replace(Regex("(https?://[^/]+).*"), "$1") + if (file.href.startsWith("/")) file.href else "/${file.href}"
                        if (file.isCollection && !folderUrl.endsWith("/")) folderUrl += "/\""""
code = code.replace(old_folder_url, new_folder_url)

# Fix parseWebDavResponse displayName and URLDecoder
old_display_name = """val displayName = prop.getElementsByTagNameNS("*", "displayname").item(0)?.textContent ?: href.trimEnd('/').substringAfterLast('/')"""
new_display_name = """var displayNameText = prop.getElementsByTagNameNS("*", "displayname").item(0)?.textContent
            if (displayNameText.isNullOrEmpty()) {
                val decoded = try { URLDecoder.decode(href.trimEnd('/').substringAfterLast('/'), "UTF-8") } catch (e: Exception) { href.trimEnd('/').substringAfterLast('/') }
                displayNameText = decoded
            }
            val displayName = displayNameText"""
code = code.replace(old_display_name, new_display_name)

# Fix episode list metadata presentation (size, date, scanlator)
# First find the block inside videoFiles.mapIndexed
old_meta_block = """                    if (showSize && file.contentLength > 0) {
                        val sizeMb = file.contentLength / (1024 * 1024)
                        this.name += " [${sizeMb}MB]"
                    }

                    val meta = episodesMeta[epNum.toInt().toString()] ?: episodesMeta[epNum.toString()]
                    if (meta?.name != null) {
                        this.name = meta.name
                    }
                    if (showDate && meta?.date_upload != null) {
                        this.date_upload = meta.date_upload
                    }
                    if (showScanlator && meta?.scanlator != null) {
                        this.scanlator = meta.scanlator
                    }"""

new_meta_block = """                    val meta = episodesMeta[epNum.toInt().toString()] ?: episodesMeta[epNum.toString()]
                    if (meta?.name != null) {
                        this.name = meta.name
                    }
                    
                    val scanlatorParts = mutableListOf<String>()
                    
                    if (showSize && file.contentLength > 0) {
                        val sizeMb = String.format(Locale.US, "%.2f MB", file.contentLength / (1024.0 * 1024.0))
                        scanlatorParts.add(sizeMb)
                    }
                    
                    if (showScanlator && meta?.scanlator != null) {
                        scanlatorParts.add(meta.scanlator)
                    }
                    
                    if (scanlatorParts.isNotEmpty()) {
                        this.scanlator = scanlatorParts.joinToString(" • ")
                    }
                    
                    if (showDate) {
                        if (meta?.date_upload != null) {
                            this.date_upload = meta.date_upload
                        } else if (file.lastModified.isNotEmpty()) {
                            try {
                                val format = SimpleDateFormat("EEE, dd MMM yyyy HH:mm:ss z", Locale.US)
                                val time = format.parse(file.lastModified)?.time
                                if (time != null) {
                                    this.date_upload = time
                                }
                            } catch (e: Exception) {}
                        }
                    }"""

if old_meta_block in code:
    code = code.replace(old_meta_block, new_meta_block)
else:
    print("WARNING: meta block not found")

with open("src/main/java/eu/kanade/tachiyomi/animeextension/all/webdav/WebDAV.kt", "w") as f:
    f.write(code)

print("Done")
