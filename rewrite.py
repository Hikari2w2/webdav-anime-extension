code = """package eu.kanade.tachiyomi.animeextension.all.webdav

import android.app.Application
import android.content.SharedPreferences
import android.util.Log
import androidx.preference.EditTextPreference
import androidx.preference.ListPreference
import androidx.preference.PreferenceScreen
import androidx.preference.SwitchPreferenceCompat
import eu.kanade.tachiyomi.animesource.AnimeSource
import eu.kanade.tachiyomi.animesource.AnimeSourceFactory
import eu.kanade.tachiyomi.animesource.ConfigurableAnimeSource
import eu.kanade.tachiyomi.animesource.model.AnimeFilterList
import eu.kanade.tachiyomi.animesource.model.AnimesPage
import eu.kanade.tachiyomi.animesource.model.SAnime
import eu.kanade.tachiyomi.animesource.model.SEpisode
import eu.kanade.tachiyomi.animesource.model.Video
import eu.kanade.tachiyomi.animesource.online.AnimeHttpSource
import eu.kanade.tachiyomi.network.GET
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.Headers
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import org.w3c.dom.Element
import uy.kohesive.injekt.Injekt
import uy.kohesive.injekt.api.get
import java.text.SimpleDateFormat
import java.util.Locale
import java.net.URLDecoder
import java.io.ByteArrayInputStream
import javax.xml.parsers.DocumentBuilderFactory

class WebDavFactory : AnimeSourceFactory {
    override fun createSources(): List<AnimeSource> {
        val prefs = Injekt.get<Application>().getSharedPreferences("webdav_global", 0x0000)
        val count = prefs.getInt("server_count", 3)
        return (1..count).map { WebDAV(it) }
    }
}

class WebDAV(private val serverId: Int) : AnimeHttpSource(), ConfigurableAnimeSource {

    override val name = "WebDAV Server $serverId"
    override val baseUrl = "http://localhost" // Not really used, we rely on user prefs
    override val lang = "all"
    override val supportsLatest = false

    private val preferences: SharedPreferences get() = 
        Injekt.get<Application>().getSharedPreferences("source_$id", 0x0000)

    private val serverUrl get() = preferences.getString(PREF_SERVER_URL, "") ?: ""
    private val username get() = preferences.getString(PREF_USERNAME, "") ?: ""
    private val password get() = preferences.getString(PREF_PASSWORD, "") ?: ""
    
    private val showSize get() = preferences.getBoolean(PREF_SHOW_SIZE, true)
    private val showDate get() = preferences.getBoolean(PREF_SHOW_DATE, true)
    private val showScanlator get() = preferences.getBoolean(PREF_SHOW_SCANLATOR, true)
    private val folderMode get() = preferences.getString(PREF_FOLDER_MODE, "structured") ?: "structured"

    private val json = Json { ignoreUnknownKeys = true }

    override fun headersBuilder(): Headers.Builder {
        val builder = super.headersBuilder()
        if (username.isNotEmpty() && password.isNotEmpty()) {
            val auth = okhttp3.Credentials.basic(username, password)
            builder.add("Authorization", auth)
        }
        return builder
    }

    private fun propfindRequest(url: String, depth: String = "1"): Request {
        val xml = \"\"\"<?xml version="1.0" encoding="utf-8" ?>
            <D:propfind xmlns:D="DAV:">
                <D:prop>
                    <D:displayname/>
                    <D:resourcetype/>
                    <D:getcontentlength/>
                    <D:getlastmodified/>
                </D:prop>
            </D:propfind>
        \"\"\".trimIndent()
        return Request.Builder()
            .url(url)
            .method("PROPFIND", xml.toRequestBody("application/xml".toMediaType()))
            .header("Depth", depth)
            .build()
    }

    private fun parseWebDavResponse(xml: String): List<WebDavFile> {
        val factory = DocumentBuilderFactory.newInstance()
        factory.isNamespaceAware = true
        val builder = factory.newDocumentBuilder()
        val doc = builder.parse(ByteArrayInputStream(xml.toByteArray()))
        val responses = doc.getElementsByTagNameNS("*", "response")
        val files = mutableListOf<WebDavFile>()

        for (i in 0 until responses.length) {
            val element = responses.item(i) as Element
            var href = element.getElementsByTagNameNS("*", "href").item(0)?.textContent ?: continue
            
            val propstat = element.getElementsByTagNameNS("*", "propstat").item(0) as? Element ?: continue
            val prop = propstat.getElementsByTagNameNS("*", "prop").item(0) as? Element ?: continue
            
            val displayNameText = prop.getElementsByTagNameNS("*", "displayname").item(0)?.textContent
            val displayName = if (displayNameText.isNullOrEmpty()) {
                try { URLDecoder.decode(href.trimEnd('/').substringAfterLast('/'), "UTF-8") } catch (e: Exception) { href.trimEnd('/').substringAfterLast('/') }
            } else {
                displayNameText
            }
            val isCollection = prop.getElementsByTagNameNS("*", "collection").length > 0 || href.endsWith("/")
            val contentLength = prop.getElementsByTagNameNS("*", "getcontentlength").item(0)?.textContent?.toLongOrNull() ?: 0L
            val lastModified = prop.getElementsByTagNameNS("*", "getlastmodified").item(0)?.textContent ?: ""

            files.add(WebDavFile(href, displayName, isCollection, contentLength, lastModified))
        }
        return files
    }

    override fun fetchPopularAnime(page: Int): rx.Observable<AnimesPage> {
        return rx.Observable.fromCallable {
            val url = serverUrl
            if (url.isEmpty()) throw Exception("Server URL not configured.")
            
            val request = propfindRequest(url)
            val response = client.newCall(request).execute()
            if (!response.isSuccessful) throw Exception("HTTP error ${response.code}")
            
            val xml = response.body?.string() ?: ""
            val files = parseWebDavResponse(xml)
            
            val rootName = url.trimEnd('/').substringAfterLast('/')
            val rootUrlNoSlash = url.replace(Regex("https?://[^/]+"), "").trimEnd('/')
            
            var orphanVideoCount = 0
            val animes = mutableListOf<SAnime>()
            
            files.forEach { file ->
                if (file.href.trimEnd('/') == rootUrlNoSlash) return@forEach
                
                if (file.isCollection) {
                    val anime = SAnime.create()
                    anime.title = file.displayName
                    var folderUrl = if (file.href.startsWith("http")) file.href else serverUrl.replace(Regex("(https?://[^/]+).*"), "$1") + if (file.href.startsWith("/")) file.href else "/${file.href}"
                    if (!folderUrl.endsWith("/")) folderUrl += "/"
                    anime.url = folderUrl
                    animes.add(anime)
                } else {
                    val nameLower = file.displayName.lowercase()
                    if (nameLower.endsWith(".mp4") || nameLower.endsWith(".mkv")) {
                        orphanVideoCount++
                    }
                }
            }
            
            if (orphanVideoCount > 0) {
                val rootAnime = SAnime.create()
                rootAnime.title = "$rootName (Root)"
                var fUrl = url
                if (!fUrl.endsWith("/")) fUrl += "/"
                fUrl += "?isRoot=true"
                rootAnime.url = fUrl
                // Insert at the beginning
                animes.add(0, rootAnime)
            }
            
            AnimesPage(animes, false)
        }
    }

    override fun fetchSearchAnime(page: Int, query: String, filters: AnimeFilterList): rx.Observable<AnimesPage> {
        return fetchPopularAnime(page).map { pageData ->
            val q = query.lowercase()
            val filtered = pageData.animes.filter { it.title.lowercase().contains(q) }
            AnimesPage(filtered, false)
        }
    }

    override fun fetchLatestUpdates(page: Int) = fetchPopularAnime(page)

    // Unused standard methods
    override fun popularAnimeRequest(page: Int): Request = throw UnsupportedOperationException()
    override fun popularAnimeParse(response: Response): AnimesPage = throw UnsupportedOperationException()
    override fun latestUpdatesRequest(page: Int): Request = throw UnsupportedOperationException()
    override fun latestUpdatesParse(response: Response): AnimesPage = throw UnsupportedOperationException()
    override fun searchAnimeRequest(page: Int, query: String, filters: AnimeFilterList): Request = throw UnsupportedOperationException()
    override fun searchAnimeParse(response: Response): AnimesPage = throw UnsupportedOperationException()

    // --- Details ---
    override fun fetchAnimeDetails(anime: SAnime): rx.Observable<SAnime> {
        return rx.Observable.fromCallable {
            val folderUrl = anime.url.substringBefore("?isRoot=true")
            
            val request = propfindRequest(folderUrl, "1")
            val response = client.newCall(request).execute()
            val xml = response.body?.string() ?: ""
            val files = parseWebDavResponse(xml)
            
            val coverFile = files.find { it.displayName.lowercase().contains("cover") }
            val detailsFile = files.find { it.displayName.equals("details.json", true) }
            
            if (coverFile != null) {
                anime.thumbnail_url = buildFullUrl(coverFile.href)
            }

            if (detailsFile != null) {
                val detailsUrl = buildFullUrl(detailsFile.href)
                val detailsReq = GET(detailsUrl, headers)
                val detailsRes = client.newCall(detailsReq).execute()
                val detailsJson = detailsRes.body?.string() ?: "{}"
                
                try {
                    val jsonObj = json.parseToJsonElement(detailsJson).jsonObject
                    jsonObj["title"]?.jsonPrimitive?.content?.let { anime.title = it }
                    jsonObj["author"]?.jsonPrimitive?.content?.let { anime.author = it }
                    jsonObj["artist"]?.jsonPrimitive?.content?.let { anime.artist = it }
                    jsonObj["description"]?.jsonPrimitive?.content?.let { anime.description = it }
                    jsonObj["genre"]?.jsonArray?.map { it.jsonPrimitive.content }?.joinToString(", ")?.let { anime.genre = it }
                    jsonObj["status"]?.jsonPrimitive?.content?.toIntOrNull()?.let { anime.status = it }
                } catch (e: Exception) { }
            }
            
            anime.initialized = true
            anime
        }
    }
    
    override fun animeDetailsParse(response: Response): SAnime = throw UnsupportedOperationException()

    // --- Episodes ---
    override fun fetchEpisodeList(anime: SAnime): rx.Observable<List<SEpisode>> {
        return rx.Observable.fromCallable {
            val isRoot = anime.url.contains("?isRoot=true")
            val folderUrl = anime.url.substringBefore("?isRoot=true")
            
            val depth = if (isRoot || folderMode == "structured") "1" else "infinity"
            
            val request = propfindRequest(folderUrl, depth)
            val response = client.newCall(request).execute()
            val xml = response.body?.string() ?: ""
            val files = parseWebDavResponse(xml)
            
            val rootUrlNoSlash = folderUrl.replace(Regex("https?://[^/]+"), "").trimEnd('/')
            
            var videoFiles = files.filter { 
                val name = it.displayName.lowercase()
                (!it.isCollection) && (name.endsWith(".mp4") || name.endsWith(".mkv"))
            }
            
            if (isRoot) {
                // Only keep files directly in the root folder
                videoFiles = videoFiles.filter {
                    val fileDir = it.href.trimEnd('/').substringBeforeLast('/')
                    fileDir == rootUrlNoSlash
                }
            }
            
            videoFiles = videoFiles.sortedBy { it.displayName }

            val episodesJsonFile = files.find { it.displayName.equals("episodes.json", true) }
            val episodesMeta = mutableMapOf<String, EpisodeMeta>()
            
            if (episodesJsonFile != null) {
                try {
                    val epRes = client.newCall(GET(buildFullUrl(episodesJsonFile.href), headers)).execute()
                    val epJsonStr = epRes.body?.string() ?: "{}"
                    val epJsonObj = json.parseToJsonElement(epJsonStr).jsonObject
                    epJsonObj.forEach { (key, value) ->
                        val obj = value.jsonObject
                        val meta = EpisodeMeta(
                            name = obj["name"]?.jsonPrimitive?.content,
                            date_upload = obj["date_upload"]?.jsonPrimitive?.content?.toLongOrNull(),
                            scanlator = obj["scanlator"]?.jsonPrimitive?.content
                        )
                        episodesMeta[key] = meta
                    }
                } catch(e: Exception) {}
            }

            videoFiles.mapIndexed { index, file ->
                SEpisode.create().apply {
                    val epNum = (index + 1).toFloat()
                    this.episode_number = epNum
                    
                    val baseName = file.displayName.substringBeforeLast(".")
                    this.name = baseName
                    this.url = buildFullUrl(file.href)
                    
                    val meta = episodesMeta[epNum.toInt().toString()] ?: episodesMeta[epNum.toString()]
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
                    } else {
                        this.scanlator = " \\u200B "
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
                    }
                }
            }.reversed()
        }
    }

    override fun episodeListParse(response: Response): List<SEpisode> = throw UnsupportedOperationException()

    // --- Videos ---
    override fun fetchVideoList(episode: SEpisode): rx.Observable<List<Video>> {
        return rx.Observable.fromCallable {
            listOf(Video(episode.url, "WebDAV Stream", episode.url, headers))
        }
    }
    
    override fun videoListParse(response: Response): List<Video> = throw UnsupportedOperationException()
    override fun videoUrlParse(response: Response): String = throw UnsupportedOperationException()

    private fun buildFullUrl(href: String): String {
        if (href.startsWith("http")) return href
        val root = serverUrl.replace(Regex("(https?://[^/]+).*"), "$1")
        return root + if (href.startsWith("/")) href else "/$href"
    }

    override fun setupPreferenceScreen(screen: PreferenceScreen) {
        val globalPrefs = Injekt.get<Application>().getSharedPreferences("webdav_global", 0x0000)

        val serverCountPref = ListPreference(screen.context).apply {
            key = "fake_key_server_count_${serverId}"
            title = "Total Server Instances (Global)"
            val currentCount = globalPrefs.getInt("server_count", 3)
            summary = "Number of WebDAV servers to show. Requires App Restart.\\nCurrent: $currentCount"
            entries = (1..10).map { it.toString() }.toTypedArray()
            entryValues = (1..10).map { it.toString() }.toTypedArray()
            setDefaultValue(currentCount.toString())
            
            setOnPreferenceChangeListener { _, newValue ->
                val count = (newValue as String).toInt()
                globalPrefs.edit().putInt("server_count", count).apply()
                summary = "Number of WebDAV servers to show. Requires App Restart.\\nCurrent: $count"
                true
            }
        }

        val folderModePref = ListPreference(screen.context).apply {
            key = PREF_FOLDER_MODE
            title = "Folder Mode"
            summary = "Structured: Subfolders only (Depth 1)\\nFlattened: All videos recursively (Depth infinity)\\nCurrent: %s"
            entries = arrayOf("Structured", "Flattened")
            entryValues = arrayOf("structured", "flattened")
            setDefaultValue("structured")
        }

        val serverPref = EditTextPreference(screen.context).apply {
            key = PREF_SERVER_URL
            title = "WebDAV Server URL"
            summary = "Base path (e.g. http://192.168.1.145:8081/Downloads/)"
            setDefaultValue("")
            dialogTitle = "Server URL"
            setOnPreferenceChangeListener { _, newValue ->
                val str = newValue as String
                summary = str.ifEmpty { "Not set" }
                true
            }
        }
        
        val userPref = EditTextPreference(screen.context).apply {
            key = PREF_USERNAME
            title = "Username"
            summary = "WebDAV Username"
            setDefaultValue("")
            dialogTitle = "Username"
        }
        
        val passPref = EditTextPreference(screen.context).apply {
            key = PREF_PASSWORD
            title = "Password"
            summary = "WebDAV Password"
            setDefaultValue("")
            dialogTitle = "Password"
        }

        val showSizePref = SwitchPreferenceCompat(screen.context).apply {
            key = PREF_SHOW_SIZE
            title = "Show File Size"
            summary = "Show video file size in episode list"
            setDefaultValue(true)
        }

        val showDatePref = SwitchPreferenceCompat(screen.context).apply {
            key = PREF_SHOW_DATE
            title = "Show Date"
            summary = "Show upload date if available"
            setDefaultValue(true)
        }

        val showScanlatorPref = SwitchPreferenceCompat(screen.context).apply {
            key = PREF_SHOW_SCANLATOR
            title = "Show Scanlator"
            summary = "Show scanlator if available"
            setDefaultValue(true)
        }

        screen.addPreference(serverCountPref)
        screen.addPreference(folderModePref)
        screen.addPreference(serverPref)
        screen.addPreference(userPref)
        screen.addPreference(passPref)
        screen.addPreference(showSizePref)
        screen.addPreference(showDatePref)
        screen.addPreference(showScanlatorPref)
    }

    companion object {
        private const val PREF_SERVER_URL = "pref_server_url"
        private const val PREF_USERNAME = "pref_username"
        private const val PREF_PASSWORD = "pref_password"
        
        private const val PREF_SHOW_SIZE = "pref_show_size"
        private const val PREF_SHOW_DATE = "pref_show_date"
        private const val PREF_SHOW_SCANLATOR = "pref_show_scanlator"
        private const val PREF_FOLDER_MODE = "pref_folder_mode"
    }
}

data class WebDavFile(
    val href: String,
    val displayName: String,
    val isCollection: Boolean,
    val contentLength: Long,
    val lastModified: String
)

data class EpisodeMeta(
    val name: String?,
    val date_upload: Long?,
    val scanlator: String?
)
"""

with open("src/main/java/eu/kanade/tachiyomi/animeextension/all/webdav/WebDAV.kt", "w") as f:
    f.write(code)

print("Done")
