with open("src/main/java/eu/kanade/tachiyomi/animeextension/all/webdav/WebDAV.kt", "r") as f:
    code = f.read()

old_meta_block = """                    if (scanlatorParts.isNotEmpty()) {
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

new_meta_block = """                    if (scanlatorParts.isNotEmpty()) {
                        this.scanlator = scanlatorParts.joinToString(" • ")
                    } else {
                        this.scanlator = " \u200B "
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
                    } else {
                        this.date_upload = -1L
                    }"""

if old_meta_block in code:
    code = code.replace(old_meta_block, new_meta_block)
else:
    print("WARNING: meta block not found")

with open("src/main/java/eu/kanade/tachiyomi/animeextension/all/webdav/WebDAV.kt", "w") as f:
    f.write(code)

print("Done")
