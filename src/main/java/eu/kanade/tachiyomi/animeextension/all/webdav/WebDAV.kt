package eu.kanade.tachiyomi.animeextension.all.webdav

import rx.Observable

import android.app.Application
import android.content.SharedPreferences
import androidx.preference.EditTextPreference
import androidx.preference.PreferenceScreen
import androidx.preference.SwitchPreferenceCompat
import eu.kanade.tachiyomi.animesource.ConfigurableAnimeSource
import eu.kanade.tachiyomi.animesource.model.AnimeFilterList
import eu.kanade.tachiyomi.animesource.model.AnimesPage
import eu.kanade.tachiyomi.animesource.model.SAnime
import eu.kanade.tachiyomi.animesource.model.SEpisode
import eu.kanade.tachiyomi.animesource.model.Video
import eu.kanade.tachiyomi.animesource.online.AnimeHttpSource
import eu.kanade.tachiyomi.network.GET
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.jsonArray
import okhttp3.Credentials
import okhttp3.Headers
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import org.w3c.dom.Element
import uy.kohesive.injekt.Injekt
import uy.kohesive.injekt.api.get
import java.io.ByteArrayInputStream
import javax.xml.parsers.DocumentBuilderFactory

class WebDAV : AnimeHttpSource(), ConfigurableAnimeSource {

    override val name = "WebDAV Anime"
    override val lang = "all"
    override val supportsLatest = true

    private val preferences: SharedPreferences get() = 
        Injekt.get<Application>().getSharedPreferences("source_$id", 0x0000)

    private val serverUrl get() = preferences.getString(PREF_SERVER_URL, "")?.trimEnd('/') ?: ""
    private val username get() = preferences.getString(PREF_USERNAME, "") ?: ""
    private val password get() = preferences.getString(PREF_PASSWORD, "") ?: ""
    
    private val showSize get() = preferences.getBoolean(PREF_SHOW_SIZE, true)
    private val showDate get() = preferences.getBoolean(PREF_SHOW_DATE, true)
    private val showScanlator get() = preferences.getBoolean(PREF_SHOW_SCANLATOR, true)

    override val baseUrl: String
        get() = serverUrl

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    override val client: OkHttpClient = network.client.newBuilder()
        .addInterceptor { chain ->
            val original = chain.request()
            val user = username
            val pass = password
            if (user.isNotEmpty() || pass.isNotEmpty()) {
                val credential = Credentials.basic(user, pass)
                val request = original.newBuilder()
                    .header("Authorization", credential)
                    .build()
                chain.proceed(request)
            } else {
                chain.proceed(original)
            }
        }
        .build()

    override fun headersBuilder(): Headers.Builder {
        val builder = super.headersBuilder()
        val user = username
        val pass = password
        if (user.isNotEmpty() || pass.isNotEmpty()) {
            builder.add("Authorization", Credentials.basic(user, pass))
        }
        return builder
    }

    private fun propfindRequest(url: String, depth: String = "1"): Request {
        val xml = """<?xml version="1.0" encoding="utf-8" ?>
            <D:propfind xmlns:D="DAV:">
                <D:prop>
                    <D:displayname/>
                    <D:resourcetype/>
                    <D:getcontentlength/>
                    <D:getlastmodified/>
                </D:prop>
            </D:propfind>
        """.trimIndent()
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
            if (href.startsWith("/")) {
                val base = serverUrl.replace(Regex("https?://[^/]+"), "")
                // Basic relative handling. A full WebDAV client does this better, but this works for most simple setups.
            }
            
            // Just use the absolute URL based on the request, or we reconstruct it.
            // Often href is path-only.
            
            val propstat = element.getElementsByTagNameNS("*", "propstat").item(0) as? Element ?: continue
            val prop = propstat.getElementsByTagNameNS("*", "prop").item(0) as? Element ?: continue
            
            val displayName = prop.getElementsByTagNameNS("*", "displayname").item(0)?.textContent ?: href.trimEnd('/').substringAfterLast('/')
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
            if (!response.isSuccessful) throw Exception("HTTP error \${response.code}")
            
            val xml = response.body?.string() ?: ""
            val files = parseWebDavResponse(xml)
            
            // The first result is usually the parent directory itself, so drop it or filter out where name is empty/same as parent.
            val animes = files.filter { it.isCollection && it.href.trimEnd('/') != url.replace(Regex("https?://[^/]+"), "").trimEnd('/') }
                .map { file ->
                    SAnime.create().apply {
                        title = file.displayName
                        // We store the full URL to the folder in url
                        val folderUrl = if (file.href.startsWith("http")) file.href else serverUrl.replace(Regex("(https?://[^/]+).*"), "$1") + file.href
                        this.url = folderUrl
                        
                        // Try to find the cover. We will need a separate PROPFIND for each folder or just let details fetch it.
                        // Wait, Aniyomi will call fetchAnimeDetails for cover anyway if we don't set it, 
                        // or we can set thumbnail_url in fetchAnimeDetails.
                    }
                }
            
            // To provide a cover immediately, we'd need to PROPFIND each folder, which is slow.
            // Let's just return the list.
            AnimesPage(animes, false)
        }
    }

    override fun fetchLatestUpdates(page: Int) = fetchPopularAnime(page)
    override fun fetchSearchAnime(page: Int, query: String, filters: AnimeFilterList) = fetchPopularAnime(page)

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
            val folderUrl = anime.url
            
            // List contents to find cover and details.json
            val request = propfindRequest(folderUrl)
            val response = client.newCall(request).execute()
            val xml = response.body?.string() ?: ""
            val files = parseWebDavResponse(xml)
            
            val detailsFile = files.find { it.displayName.equals("details.json", true) }
            val coverFile = files.find { 
                val name = it.displayName.lowercase()
                name.contains("cover") && (name.endsWith(".jpg") || name.endsWith(".jpeg") || name.endsWith(".png") || name.endsWith(".webp"))
            }

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
                } catch (e: Exception) {
                    // Ignore parsing errors
                }
            }
            
            anime.initialized = true
            anime
        }
    }
    
    override fun animeDetailsParse(response: Response): SAnime = throw UnsupportedOperationException()

    // --- Episodes ---
    override fun fetchEpisodeList(anime: SAnime): rx.Observable<List<SEpisode>> {
        return rx.Observable.fromCallable {
            val folderUrl = anime.url
            
            val request = propfindRequest(folderUrl)
            val response = client.newCall(request).execute()
            val xml = response.body?.string() ?: ""
            val files = parseWebDavResponse(xml)
            
            val videoFiles = files.filter { 
                val name = it.displayName.lowercase()
                name.endsWith(".mp4") || name.endsWith(".mkv")
            }.sortedBy { it.displayName }

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
                    this.url = buildFullUrl(file.href) // We store direct file url
                    
                    if (showSize && file.contentLength > 0) {
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
                    }
                }
            }.reversed() // Aniyomi expects newest first usually
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
        val serverPref = EditTextPreference(screen.context).apply {
            key = PREF_SERVER_URL
            title = "WebDAV Server URL"
            summary = "Base path to the Anime directory (e.g. https://domain.com/webdav/Anime)"
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
            summary = "Show upload date if available in episodes.json"
            setDefaultValue(true)
        }

        val showScanlatorPref = SwitchPreferenceCompat(screen.context).apply {
            key = PREF_SHOW_SCANLATOR
            title = "Show Scanlator"
            summary = "Show scanlator if available in episodes.json"
            setDefaultValue(true)
        }

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
