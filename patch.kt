import java.text.SimpleDateFormat
import java.util.Locale

fun parseWebDavDate(dateStr: String): Long {
    return try {
        val format = SimpleDateFormat("EEE, dd MMM yyyy HH:mm:ss z", Locale.US)
        format.parse(dateStr)?.time ?: 0L
    } catch(e: Exception) {
        0L
    }
}
